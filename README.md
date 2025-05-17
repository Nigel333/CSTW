# CSTW
Thesis website


TO INSTALL CLOUDFARE:
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb
cloudflared tunnel --url http://localhost:5000

Then replace the link wihtin record.js with the generated public url from cloudfare
restart localhost terminal then it would work
