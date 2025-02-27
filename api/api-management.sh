#!/bin/bash

# Konfigurasi Dasar
CONFIG_PATH="/etc/vpn-api/config.json"
USER_DB="/etc/vpn-api/users.json"
XRAY_CONFIG="/etc/xray/config.json"

# Validasi API Key
validate_api_key() {
    local provided_key="$1"
    local stored_key=$(jq -r '.api_key' "$CONFIG_PATH")
    
    if [[ "$provided_key" != "$stored_key" ]]; then
        echo "{\"status\": \"error\", \"message\": \"Invalid API Key\"}"
        exit 1
    fi
}

# Fungsi untuk memeriksa apakah user sudah ada
is_user_exists() {
    local username="$1"
    
    # Cek apakah user dengan username sudah ada
    jq -e --arg username "$username" \
        '.users[] | select(.username == $username)' \
        "$USER_DB" > /dev/null
}

# Modifikasi fungsi add_user untuk meminta input tambahan
add_user() {
    local username="$1"
    local protocol="$2"
    local validity_days="${3:-30}"
    local quota="${4:-100}"      
    local ip_limit="${5:-3}"     

    # Generate UUID
    local uuid=$(uuidgen)
    local expiry_date=$(date -d "+$validity_days days" +"%Y-%m-%d")
    local domain=$(cat /etc/xray/domain)

    # Fungsi generate link untuk setiap protokol
    generate_protocol_links() {
        local protocol="$1"
        local username="$2"
        local uuid="$3"
        local domain="$4"

        case "$protocol" in
            "vmess")
                # TLS Link
                local vmess_tls=$(cat <<EOF
{
    "v": "2",
    "ps": "$username",
    "add": "$domain",
    "port": "443",
    "id": "$uuid",
    "aid": "0",
    "net": "ws",
    "path": "/vmess",
    "type": "none",
    "host": "$domain",
    "tls": "tls"
}
EOF
)
                local vmess_tls_link="vmess://$(echo "$vmess_tls" | base64 -w 0)"

                # Non-TLS Link
                local vmess_non_tls=$(cat <<EOF
{
    "v": "2",
    "ps": "$username",
    "add": "$domain",
    "port": "80",
    "id": "$uuid",
    "aid": "0",
    "net": "ws",
    "path": "/vmess",
    "type": "none",
    "host": "$domain",
    "tls": "none"
}
EOF
)
                local vmess_non_tls_link="vmess://$(echo "$vmess_non_tls" | base64 -w 0)"

                # gRPC Link
                local vmess_grpc=$(cat <<EOF
{
    "v": "2",
    "ps": "$username",
    "add": "$domain",
    "port": "443",
    "id": "$uuid",
    "aid": "0",
    "net": "grpc",
    "path": "vmess-grpc",
    "type": "none",
    "host": "$domain",
    "tls": "tls"
}
EOF
)
                local vmess_grpc_link="vmess://$(echo "$vmess_grpc" | base64 -w 0)"

                echo "{\"tls_link\":\"$vmess_tls_link\",\"non_tls_link\":\"$vmess_non_tls_link\",\"grpc_link\":\"$vmess_grpc_link\"}"
                ;;

            "vless")
                # TLS Link
                local vless_tls_link="vless://${uuid}@${domain}:443?path=/vless&security=tls&encryption=none&type=ws#${username}"
                
                # Non-TLS Link
                local vless_ntls_link="vless://${uuid}@${domain}:80?path=/vless&encryption=none&type=ws#${username}"
                
                # gRPC Link
                local vless_grpc_link="vless://${uuid}@${domain}:443?mode=gun&security=tls&encryption=none&type=grpc&serviceName=vless-grpc&sni=${domain}#${username}"

                echo "{\"tls_link\":\"$vless_tls_link\",\"non_tls_link\":\"$vless_ntls_link\",\"grpc_link\":\"$vless_grpc_link\"}"
                ;;

            "trojan")
                # TLS WS Link
                local trojan_tls_link="trojan://${uuid}@${domain}:443?path=%2Ftrojan-ws&security=tls&host=${domain}&type=ws&sni=${domain}#${username}"
                
                # Non-TLS WS Link
                local trojan_ntls_link="trojan://${uuid}@${domain}:80?path=%2Ftrojan-ws&security=none&host=${domain}&type=ws#${username}"
                
                # gRPC Link
                local trojan_grpc_link="trojan://${uuid}@${domain}:443?mode=gun&security=tls&type=grpc&serviceName=trojan-grpc&sni=${domain}#${username}"

                echo "{\"tls_link\":\"$trojan_tls_link\",\"non_tls_link\":\"$trojan_ntls_link\",\"grpc_link\":\"$trojan_grpc_link\"}"
                ;;
        esac
    }

    # Tambah user ke database dengan domain
    jq --arg username "$username" \
       --arg uuid "$uuid" \
       --arg protocol "$protocol" \
       --arg expiry "$expiry_date" \
       --arg quota "$quota" \
       --arg iplimit "$ip_limit" \
       --arg domain "$domain" \
       '.users += [{"username": $username, "uuid": $uuid, "protocol": $protocol, "expiry": $expiry, "quota": $quota, "iplimit": $iplimit, "domain": $domain}]' \
       "$USER_DB" > temp.json && mv temp.json "$USER_DB"

    # Generate konfigurasi dan catat user sesuai protokol
    case "$protocol" in
        "vmess")
            generate_vmess_config "$uuid" "$username"
            ;;
        "vless")
            generate_vless_config "$uuid" "$username"
            ;;
        "trojan")
            generate_trojan_config "$uuid" "$username"
            ;;
    esac

    # Generate links
    local protocol_links=$(generate_protocol_links "$protocol" "$username" "$uuid" "$domain")

    # Keluarkan informasi dengan tambahan links
    echo "{\"status\": \"success\", \"username\": \"$username\", \"uuid\": \"$uuid\", \"expiry\": \"$expiry_date\", \"quota\": \"$quota\", \"iplimit\": \"$ip_limit\", \"domain\": \"$domain\", \"links\": $protocol_links}"
}

# Fungsi generate konfigurasi Vmess
generate_vmess_config() {
    local uuid="$1"
    local username="$2"
    local quota="${3:-100}"
    local ip_limit="${4:-3}"
    local config_path="/etc/xray/config.json"
    local domain=$(cat /etc/xray/domain)
    local exp=$(date -d "+3 days" +"%Y-%m-%d")  # Default 3 hari

    # Tambahkan user ke konfigurasi Vmess WS
    sed -i '/#vmess$/a\### '"$username $exp"'\
},{"id": "'""$uuid""'","alterId": '"0"',"email": "'""$username""'"' "$config_path"

    # Tambahkan user ke konfigurasi Vmess gRPC
    sed -i '/#vmessgrpc$/a\### '"$username $exp"'\
},{"id": "'""$uuid""'","alterId": '"0"',"email": "'""$username""'"' "$config_path"

    # Buat file konfigurasi klien
    mkdir -p /var/www/html
    cat > "/var/www/html/vmess-$username.txt" <<-END
[server]
remarks = $username
server = $domain
port = 443
type = vmess
id = $uuid
alterId = 0
network = ws
path = /vmess
tls = true
allowInsecure = false
END

    # Hapus entri lama jika sudah ada sebelum menambahkan
    if [[ -f "/etc/vmess/.vmess.db" ]]; then
        # Hapus baris dengan username yang sama
        sed -i "/\b${username}\b/d" "/etc/vmess/.vmess.db"
    fi
    # Tambahkan entri baru
    echo "### ${username} ${exp} ${uuid} ${quota} ${ip_limit}" >> "/etc/vmess/.vmess.db"

    # Buat direktori jika belum ada
    mkdir -p /etc/vmess
    mkdir -p /etc/kyt/limit/vmess/ip

    # Atur limit IP (default 3)
    echo "3" > /etc/kyt/limit/vmess/ip/$username

    # Atur quota (default 100 GB)
    local quota_bytes=$((100 * 1024 * 1024 * 1024))
    echo "$quota_bytes" > /etc/vmess/$username

    # Restart Xray
    systemctl restart xray

    return 0
}
# Fungsi generate konfigurasi Vless
generate_vless_config() {
    local uuid="$1"
    local username="$2"
    local quota="${3:-100}"
    local ip_limit="${4:-3}"
    local config_path="/etc/xray/config.json"
    local domain=$(cat /etc/xray/domain)
    local exp=$(date -d "+3 days" +"%Y-%m-%d")  # Default 3 hari

    # Tambahkan user ke konfigurasi Vless WS
    sed -i '/#vless$/a\### '"$username $exp"'\
},{"id": "'""$uuid""'","email": "'""$username""'"' "$config_path"

    # Tambahkan user ke konfigurasi Vless gRPC
    sed -i '/#vlessgrpc$/a\### '"$username $exp"'\
},{"id": "'""$uuid""'","email": "'""$username""'"' "$config_path"

    # Buat file konfigurasi klien
    mkdir -p /var/www/html
    cat > "/var/www/html/vless-$username.txt" <<-END
[server]
remarks = $username
server = $domain
port = 443
type = vless
id = $uuid
network = ws
path = /vless
tls = true
allowInsecure = false
END

    # Hapus entri lama jika sudah ada sebelum menambahkan
    if [[ -f "/etc/vless/.vless.db" ]]; then
        # Hapus baris dengan username yang sama
        sed -i "/\b${username}\b/d" "/etc/vless/.vless.db"
    fi
    # Tambahkan entri baru
    echo "### ${username} ${exp} ${uuid} ${quota} ${ip_limit}" >> "/etc/vless/.vless.db"

    # Buat direktori jika belum ada
    mkdir -p /etc/vless
    mkdir -p /etc/kyt/limit/vless/ip

    # Atur limit IP (default 3)
    echo "3" > /etc/kyt/limit/vless/ip/$username

    # Atur quota (default 100 GB)
    local quota_bytes=$((100 * 1024 * 1024 * 1024))
    echo "$quota_bytes" > /etc/vless/$username

    # Restart Xray
    systemctl restart xray

    return 0
}

# Fungsi generate konfigurasi Trojan
generate_trojan_config() {
    local uuid="$1"
    local username="$2"
    local quota="${3:-100}"
    local ip_limit="${4:-3}"
    local config_path="/etc/xray/config.json"
    local domain=$(cat /etc/xray/domain)
    local exp=$(date -d "+3 days" +"%Y-%m-%d")  # Default 3 hari

    # Tambahkan user ke konfigurasi Trojan WS
    sed -i '/#trojan$/a\### '"$username $exp"'\
},{"password": "'""$uuid""'","email": "'""$username""'"' "$config_path"

    # Tambahkan user ke konfigurasi Trojan gRPC
    sed -i '/#trojangrpc$/a\### '"$username $exp"'\
},{"password": "'""$uuid""'","email": "'""$username""'"' "$config_path"

    # Buat file konfigurasi klien
    mkdir -p /var/www/html
    cat > "/var/www/html/trojan-$username.txt" <<-END
[server]
remarks = $username
server = $domain
port = 443
type = trojan
password = $uuid
network = ws
path = /trojan
tls = true
allowInsecure = false
END

   # Hapus entri lama jika sudah ada sebelum menambahkan
    if [[ -f "/etc/trojan/.trojan.db" ]]; then
        # Hapus baris dengan username yang sama
        sed -i "/\b${username}\b/d" "/etc/trojan/.trojan.db"
    fi
    # Tambahkan entri baru
    echo "### ${username} ${exp} ${uuid} ${quota} ${ip_limit}" >> "/etc/trojan/.trojan.db"

    # Buat direktori jika belum ada
    mkdir -p /etc/trojan
    mkdir -p /etc/kyt/limit/trojan/ip

    # Atur limit IP (default 3)
    echo "3" > /etc/kyt/limit/trojan/ip/$username

    # Atur quota (default 100 GB)
    local quota_bytes=$((100 * 1024 * 1024 * 1024))
    echo "$quota_bytes" > /etc/trojan/$username

    # Restart Xray
    systemctl restart xray

    return 0
}

# Fungsi hapus user dari konfigurasi Vmess
remove_vmess_user() {
    local username="$1"
    local config_path="/etc/xray/config.json"
    
    # Hapus user dari konfigurasi Vmess WS
    sed -i "/### $username /d" "$config_path"
    sed -i "/\"email\": \"$username\"/,/},/d" "$config_path"
    
    # Hapus dari konfigurasi Vmess gRPC
    sed -i "/### $username /d" "$config_path"
    sed -i "/\"email\": \"$username\"/,/},/d" "$config_path"
}

# Fungsi hapus user dari konfigurasi Vless
remove_vless_user() {
    local username="$1"
    local config_path="/etc/xray/config.json"
    
    # Hapus user dari konfigurasi Vless WS
    sed -i "/### $username /d" "$config_path"
    sed -i "/\"email\": \"$username\"/,/},/d" "$config_path"
    
    # Hapus dari konfigurasi Vless gRPC
    sed -i "/### $username /d" "$config_path"
    sed -i "/\"email\": \"$username\"/,/},/d" "$config_path"
}

# Fungsi hapus user dari konfigurasi Trojan
remove_trojan_user() {
    local username="$1"
    local config_path="/etc/xray/config.json"
    
    # Hapus user dari konfigurasi Trojan WS
    sed -i "/### $username /d" "$config_path"
    sed -i "/\"email\": \"$username\"/,/},/d" "$config_path"
    
    # Hapus dari konfigurasi Trojan gRPC
    sed -i "/### $username /d" "$config_path"
    sed -i "/\"email\": \"$username\"/,/},/d" "$config_path"
}

# Fungsi validasi user sebelum menghapus
validate_user_for_deletion() {
    local username="$1"
    local protocol="$2"
    local config_path="/etc/vpn-api/config.json"
    local user_db="/etc/vpn-api/users.json"

    # Validasi username tidak kosong
    if [[ -z "$username" ]]; then
        echo "Error: Username tidak boleh kosong" >&2
        return 1
    fi

    # Validasi protokol tidak kosong
    if [[ -z "$protocol" ]]; then
        echo "Error: Protokol tidak boleh kosong" >&2
        return 1
    fi

    # Validasi protokol
    case "$protocol" in
        "vmess"|"vless"|"trojan")
            # Protokol valid, lanjutkan
            ;;
        *)
            echo "Error: Protokol tidak valid. Gunakan vmess/vless/trojan" >&2
            return 1
            ;;
    esac

    # Periksa apakah user ada di database dengan protokol spesifik
    local user_exists=$(jq --arg username "$username" --arg protocol "$protocol" \
        '.users[] | select(.username == $username and .protocol == $protocol)' "$user_db")
    
    if [[ -z "$user_exists" ]]; then
        echo "Error: User '$username' dengan protokol '$protocol' tidak ditemukan" >&2
        return 1
    fi

    return 0
}

# Fungsi hapus user
delete_user() {
    local username="$1"
    local protocol="$2"
    local config_path="/etc/xray/config.json"
    local user_db="/etc/vpn-api/users.json"

    # Validasi user
    if ! validate_user_for_deletion "$username" "$protocol"; then
        echo "{\"status\": \"error\", \"message\": \"Validasi gagal\"}"
        exit 1
    fi

    # Ambil UUID user untuk logging
    local uuid=$(jq -r --arg username "$username" --arg protocol "$protocol" \
        '.users[] | select(.username == $username and .protocol == $protocol) | .uuid' "$user_db")

    # Hapus dari database user
    jq --arg username "$username" --arg protocol "$protocol" \
        'del(.users[] | select(.username == $username and .protocol == $protocol))' \
        "$user_db" > temp.json && mv temp.json "$user_db"

    # Hapus dari konfigurasi Xray sesuai protokol
    case "$protocol" in
        "vmess")
            remove_vmess_user "$username"
            ;;
        "vless")
            remove_vless_user "$username"
            ;;
        "trojan")
            remove_trojan_user "$username"
            ;;
    esac

    # Hapus file pendukung
    rm -f "/var/www/html/${protocol}-$username.txt"
    rm -f "/etc/kyt/limit/${protocol}/ip/$username"
    rm -f "/etc/files/${protocol}/$username"
    
    # Hapus dari database protokol spesifik
    sed -i "/\b${username}\b/d" "/etc/${protocol}/.${protocol}.db"

    # Restart Xray
    systemctl restart xray

    # Keluarkan konfirmasi dengan tambahan UUID
    echo "{\"status\": \"success\", \"message\": \"User $username ($protocol) berhasil dihapus\", \"uuid\": \"$uuid\"}"
}
# Main
main() {
    # Validasi API Key
    validate_api_key "$1"
    
    # Aksi
    case "$2" in
        "add")
            # Tambahkan parameter quota dan ip_limit dengan default
            add_user "$3" "$4" "$5" "${6:-100}" "${7:-3}"
            ;;
        "delete")
            delete_user "$3" "$4"
            ;;
        *)
            echo "{\"status\": \"error\", \"message\": \"Aksi tidak valid\"}"
            exit 1
            ;;
    esac
}

# Jalankan
main "$@"
