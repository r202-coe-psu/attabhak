import asyncio
import datetime
import logging
import struct

logger = logging.getLogger("attabhak")


IDLE_TIMEOUT = 1.0
RECV_CHUNK = 4096
CONNECT_TIMEOUT = 5.0

EREC_FMT = "<8sIfHfHffff7HffH"
EREC_BODY_LEN = struct.calcsize(EREC_FMT)  # 64

INT_TIMES = [15, 20, 30, 40, 45, 60]
HEATER = ["off", "RH", "Temp"]
PUMP = ["off", "on"]


def _bit(value, n):
    return (value >> n) & 1


def decode_erec(data: bytes) -> dict:
    if len(data) < EREC_BODY_LEN:
        raise ValueError(
            f"Packet too short: {len(data)} bytes, need {EREC_BODY_LEN}"
        )

    (td, flags, conc, n5, avg24, n7, coef, bkg, rng, flow,
     a_rh, a_inst, a_pres, a_det, a_flow, pump, heater,
     temp_th, rh_th, int_idx) = struct.unpack_from(EREC_FMT, data)

    # Time/date: inferred from captures (byte3=hour, byte4=minute,
    # byte5=month, byte6=day, byte7=year offset from 1950?). Verify!
    hour, minute, month, day, yy = td[3], td[4], td[5], td[6], td[7]

    try:
        # instrument clock is assumed to run in the host's local timezone
        record_time = datetime.datetime(1950 + yy, month, day, hour, minute).astimezone()
    except ValueError:
        record_time = None

    return {
        "record_time": record_time,
        "time": f"{hour:02d}:{minute:02d}",
        "date": f"{month:02d}-{day:02d}-{(1950 + yy) % 100:02d}",
        "time_date_raw": td.hex(" "),
        "flags": f"0x{flags:08X}",
        "conc_units": "mg/m3" if _bit(flags, 27) else "ug/m3",
        "temp_comp": "std" if _bit(flags, 22) else "act",
        "pres_comp": "std" if _bit(flags, 24) else "act",
        "filter_control": "move" if _bit(flags, 16) else "stop",
        "concentration": round(conc, 3),
        "conc_status": n5,
        "avg_24hr": round(avg24, 3),
        "avg_status": n7,
        "coefficient": round(coef, 3),
        "background": round(bkg, 1),
        "range": rng,
        "flow_lpm": round(flow, 3),
        "alarm_rh_temp": a_rh,
        "alarm_instrument": a_inst,
        "alarm_pressure": a_pres,
        "alarm_detector": a_det,
        "alarm_flow": a_flow,
        "pump": PUMP[pump] if pump < len(PUMP) else pump,
        "heater": HEATER[heater] if heater < len(HEATER) else heater,
        "temp_threshold": temp_th,
        "rh_threshold": rh_th,
        "int_time_min": INT_TIMES[int_idx] if int_idx < len(INT_TIMES) else int_idx,
        "trailer": data[EREC_BODY_LEN:].hex(" "),
    }


def format_erec(rec: dict) -> str:
    units = rec["conc_units"]
    alarms = [k[6:] for k in rec if k.startswith("alarm_") and rec[k]]
    return "\n".join(
        [
            f"Time / Date      : {rec['time']}  {rec['date']}   (raw {rec['time_date_raw']})",
            f"Concentration    : {rec['concentration']} {units}",
            f"24-hr Average    : {rec['avg_24hr']} {units}",
            f"Flow             : {rec['flow_lpm']} L/min",
            f"Coefficient      : {rec['coefficient']:.3f}",
            f"Background       : {rec['background']}",
            f"Range            : {rec['range']:g}",
            f"Alarms           : {', '.join(alarms) if alarms else 'none'}",
            f"Pump / Heater    : {rec['pump']} / {rec['heater']}",
            f"Temp / RH thresh : {rec['temp_threshold']:g} / {rec['rh_threshold']:g}",
            f"Int time         : {rec['int_time_min']} min",
            f"Temp/Pres comp   : {rec['temp_comp']} / {rec['pres_comp']}",
            f"Filter control   : {rec['filter_control']}",
            f"Flags            : {rec['flags']}",
            f"Trailer          : {rec['trailer']}",
        ]
    )


class ThermoScientificClient:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.reader = None
        self.writer = None

    async def init(self):
        logger.debug("Initialing")
        try:
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.ip, self.port), CONNECT_TIMEOUT
            )
        except (OSError, asyncio.TimeoutError) as e:
            logger.warning(
                "Thermo Scientific: unable to connect to %s:%s (%r)",
                self.ip, self.port, e,
            )
            await self.close()
            return False

        logger.debug("Initial successfully")
        return True

    async def setup(self):
        if not await self.init():
            return False

        for cmd in (
            "Program No",
            "Instr Name",
            "Set Mode Remote",
            "Set Format 01",
            "ERec Layout",
            "LRec Mem Size",
            "SRec Mem Size",
        ):
            reply = await self.send_msg(cmd)
            logger.debug("> %s < %r", cmd, reply)

        screen = await self.send_msg("IScreen")
        logger.debug("> IScreen (%d bytes of screen bitmap)", len(screen or b""))

        return True

    async def close(self):
        try:
            if self.writer:
                self.writer.close()
                await self.writer.wait_closed()
        except Exception as e:
            logger.exception(e)

        self.reader = None
        self.writer = None
        logger.debug("Thermo Scientific closed socket connection")

    async def send_msg(self, cmd: str, idle_timeout: float = IDLE_TIMEOUT):
        if not self.writer or self.writer.is_closing():
            logger.debug("Socket is not connected, reconnecting")
            await self.close()
            if not await self.init():
                return None

        try:
            self.writer.write(cmd.encode("ascii") + b"\r")
            await self.writer.drain()
            return await self.recv_response(idle_timeout)
        except OSError:
            logger.debug("Cannot send/receive messages")
            await self.close()
            return None

    async def recv_response(self, idle_timeout: float = IDLE_TIMEOUT) -> bytes:
        """Read until the stream goes quiet for idle_timeout seconds.

        Handles both single-segment ASCII replies and multi-segment binary
        replies (e.g. IScreen, which arrives as several TCP segments).
        """
        data = bytearray()
        while True:
            try:
                chunk = await asyncio.wait_for(
                    self.reader.read(RECV_CHUNK), idle_timeout
                )
            except asyncio.TimeoutError:
                break
            if not chunk:
                # remote closed the connection
                await self.close()
                break
            data.extend(chunk)
        return bytes(data)

    async def read_sensor(self):
        record = await self.send_msg("ER12")
        if record is None:
            logger.warning("Thermo Scientific: not connected, skip reading")
            return {}
        if not record:
            logger.warning("Thermo Scientific: empty ER12 response")
            return {}

        try:
            rec = decode_erec(record)
        except (ValueError, struct.error) as e:
            logger.warning("Thermo Scientific: cannot decode ER12 (%s): %r", e, record)
            return {}

        # logger.debug("ER12 (%d bytes)\n%s", len(record), format_erec(rec))

        conc = rec["concentration"]
        avg_24h = rec["avg_24hr"]
        if rec["conc_units"] == "mg/m3":
            # convert mg/m3 to ug/m3
            conc *= 1000
            avg_24h *= 1000

        now = datetime.datetime.now(datetime.timezone.utc)
        record_time = rec["record_time"]
        if record_time is None:
            logger.warning(
                "Thermo Scientific: invalid record time %s, using host time",
                rec["time_date_raw"],
            )
            record_time = now

        data = {
            "timestamp": now.timestamp(),
            # instrument record time (UTC unix time); upload_data drops repeated runtimes
            "runtime": int(record_time.timestamp()),
            "pm_2_5": round(conc, 3),
            "pm_2_5_avg_24h": round(avg_24h, 3),
            "flow_lpm": rec["flow_lpm"],
        }


        return data
