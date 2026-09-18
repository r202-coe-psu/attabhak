echo "copy attabahk service file"
USER='tl'
sudo cp /home/$USER/attabhak/scripts/attabhak.service /lib/systemd/system
sudo cp /home/$USER/attabhak/scripts/etc/logrotate.d/attabhak /etc/logrotate.d/attabhak

if [ ! -d /var/log/attabhak ]
then
    echo "create log directory"
    sudo mkdir /var/log/attabhak
    sudo chown -R $USER: /var/log/attabhak
else
    echo "attabhak log found"
fi


echo "enable service"
sudo service logrotate restart
sudo systemctl daemon-reload
sudo systemctl enable attabhak.service

