# NOTE README.md
# UP REPO DEBIAN
<pre><code>apt update -y && apt upgrade -y && apt dist-upgrade -y && reboot</code></pre>
# UP REPO UBUNTU
<pre><code>apt update && apt upgrade -y && update-grub && sleep 2 && reboot</pre></code>

### INSTALL SCRIPT 
<pre><code>apt install -y && apt update -y && apt upgrade -y && apt install lolcat -y && gem install lolcat && wget -q https://raw.githubusercontent.com/zxeeds/vip-script/main/main.sh && chmod +x main.sh && ./main.sh
</code></pre>

### PERINTAH UPDATE 
<pre><code>wget https://raw.githubusercontent.com/zxeeds/vip-script/main/files/update && chmod +x update && ./update</code></pre>

### TESTED ON OS 
- UBUNTU 20
- DEBIAN 10 ( Recomended )

### PORT INFO
```
- TROJAN WS  443 8443
- TROJAN GRPC 443 8443
- SHADOWSOCKS WS 443 8443
- SHADOWSOCKS GRPC 443 8443
- VLESS WSS 443 8443
- VLESS GRPC 443 8443
- VLESS NONTLS 80 8080 8880 2082
- VMESS WS 443 8443
- VMESS GRPC 443 8443
- VMESS NONTLS 80 8080 8880 2082
- SSH WS / TLS 443 8443
- SSH NON TLS 8880 80 8080 2082 2095 2086
- OVPN SSL/TCP 1194
- SLOWDNS 5300
```
### Author
```
VIP DIGITAL :
<a href="https://t.me/sannpro" target=”_blank”>SANN PRO</a><br>
```
```
``
```
repository/
│
├── main.sh                 # Script utama instalasi VPN
├── api-management.sh       # Script manajemen API user
├── README.md               # Dokumentasi project
│
├── cfg/                    # Folder konfigurasi
│   ├── xray-config.json    # Template konfigurasi Xray
│   ├── haproxy.cfg         # Konfigurasi HAProxy
│   ├── nginx.conf          # Konfigurasi Nginx
│   └── dropbear.conf       # Konfigurasi Dropbear
│
├── files/                  # Folder file pendukung
│   ├── limit.sh            # Script pembatasan
│   ├── ws                  # WebSocket proxy
│   ├── nameserver          # Konfigurasi DNS
│   └── bbr.sh              # Script konfigurasi BBR
│
├── banner/                 # Folder banner
│   └── issue.net           # Banner login
│
├── Features/               # Folder fitur tambahan
│   └── menu.zip            # Menu manajemen
│
└── api/                    # Folder API
    ├── config.json         # Konfigurasi API
    ├── users.json          # Database user
    └── logs/               # Folder log API
        ├── access.log
        └── error.log
