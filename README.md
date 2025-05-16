# NOTE README.md

# UP REPO DEBIAN

<pre><code>apt update -y && apt upgrade -y && apt dist-upgrade -y && reboot</code></pre>

# UP REPO UBUNTU

<pre><code>apt update && apt upgrade -y && update-grub && sleep 2 && reboot</pre></code>

### INSTALL SCRIPT

<pre><code>apt install -y && apt update -y && apt upgrade -y && apt install lolcat -y && gem install lolcat && wget https://raw.githubusercontent.com/zxeeds/vip-script/main/main.sh && chmod +x main.sh && ./main.sh
</code></pre>

### INSTALL API

<pre><code>wget https://raw.githubusercontent.com/zxeeds/vip-script/main/api-install.sh && chmod +x api-install.sh && ./api-install.sh
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

VIP DIGITAL :
<a href="https://t.me/sannpro" target=”_blank”>SANN PRO</a><br>

### Repository

```
vip-script/
│
├── main.sh                 # Script utama (orkestrator)
├── api-install.sh          # Script manajemen API user
├── README.md               # Dokumentasi project
│
├── modules/                # Folder baru untuk modul-modul instalasi
│   ├── system_prep.sh      # Persiapan sistem
│   ├── web_server.sh       # Instalasi Nginx dan HAProxy
│   ├── xray.sh             # Instalasi Xray
│   ├── ssh.sh              # Konfigurasi SSH dan Dropbear
│   ├── vpn.sh              # Instalasi OpenVPN
│   ├── dns.sh              # Konfigurasi SlowDNS
│   ├── security.sh         # Instalasi Fail2ban
│   ├── backup.sh           # Sistem backup
│   └── menu.sh             # Instalasi menu
│
├── lib/                    # Folder baru untuk fungsi-fungsi umum
│   ├── common.sh           # Fungsi umum (warna, logging)
│   ├── progress.sh         # Fungsi progress bar
│   └── error_handling.sh   # Fungsi error handling
│
├── cfg/                    # Folder konfigurasi (tetap sama)
│   ├── xray-config.json    # Template konfigurasi Xray
│   ├── haproxy.cfg         # Konfigurasi HAProxy
│   ├── nginx.conf          # Konfigurasi Nginx
│   └── dropbear.conf       # Konfigurasi Dropbear
│
├── files/                  # Folder file pendukung (tetap sama)
│   ├── limit.sh            # Script pembatasan
│   ├── ws                  # WebSocket proxy
│   ├── nameserver          # Konfigurasi DNS
│   └── bbr.sh              # Script konfigurasi BBR
│
├── banner/                 # Folder banner (tetap sama)
│   └── issue.net           # Banner login
│
├── Features/               # Folder fitur tambahan (tetap sama)
│   └── menu.zip            # Menu manajemen
│
└── api/                    # Folder API (tetap sama)
```
