from Crypto.Cipher import AES
from Crypto.Cipher._mode_cbc import CbcMode
from typing import Optional
import hashlib
import hmac
import base64
import requests
import os
import uuid

appInfo = {
    "image": b"WhatsApp Image Keys",
    "video": b"WhatsApp Video Keys",
    "audio": b"WhatsApp Audio Keys",
    "document": b"WhatsApp Document Keys",
    "image/webp": b"WhatsApp Image Keys",
    "image/jpeg": b"WhatsApp Image Keys",
    "image/png": b"WhatsApp Image Keys",
    "video/mp4": b"WhatsApp Video Keys",
    "audio/aac": b"WhatsApp Audio Keys",
    "audio/ogg": b"WhatsApp Audio Keys",
    "audio/wav": b"WhatsApp Audio Keys",
}

extension = {
    "image": "jpg",
    "video": "mp4",
    "audio": "ogg",
    "document": "bin",
}


def HKDF(key: bytes, length: int, appInfo: bytes = b"") -> bytes:
    key = hmac.new(b"\0" * 32, key, hashlib.sha256).digest()
    keyStream = b""
    keyBlock = b""
    blockIndex = 1
    while len(keyStream) < length:
        keyBlock = hmac.new(
            key,
            msg=keyBlock + appInfo + (chr(blockIndex).encode("utf-8")),
            digestmod=hashlib.sha256,
        ).digest()
        blockIndex += 1
        keyStream += keyBlock
    return keyStream[:length]


def AESUnpad(s: bytes) -> bytes:
    return s[: -ord(s[len(s) - 1 :])]


def AESDecrypt(key: bytes, ciphertext: bytes, iv: Optional[bytes]) -> bytes:
    cipher: CbcMode = AES.new(key, AES.MODE_CBC, iv)  # type: ignore
    plaintext: bytes = cipher.decrypt(ciphertext)
    return AESUnpad(plaintext)


def decryptByName(
    fileName: bytes, mediaKey: bytes, mediaType: str, output: Optional[bytes] = None
) -> bool:
    mediaKeyExpanded: bytes = HKDF(mediaKey, 112, appInfo[mediaType])
    mediaData: bytes = open(fileName, "rb").read()

    file: bytes = mediaData[:-10]

    data: bytes = AESDecrypt(mediaKeyExpanded[16:48], file, mediaKeyExpanded[:16])

    if output is None:
        if "/" in mediaType:
            fileExtension = mediaType.split("/")[1]
        else:
            fileExtension: str = extension[mediaType]

        output = fileName.replace(b".enc", f".{fileExtension}".encode("utf-8"))
    with open(output, "wb") as f:
        f.write(data)

    return True


def decryptByLink(
    link: str,
    mediaKey: bytes,
    mediaType: str,
    ngrok_url: str,
    output: Optional[str] = None,
) -> str:
    """
    Descriptografa arquivo do WhatsApp e retorna URL pública via ngrok
    """
    try:
        response: requests.Response = requests.get(link, timeout=30)
        if response.status_code != 200:
            raise Exception(f"Erro ao baixar arquivo: {response.status_code}")
        mediaData: bytes = response.content

        mediaKeyExpanded: bytes = HKDF(mediaKey, 112, appInfo[mediaType])
        file: bytes = mediaData[:-10]
        data: bytes = AESDecrypt(mediaKeyExpanded[16:48], file, mediaKeyExpanded[:16])

        # Determina extensão do arquivo
        if "/" in mediaType:
            fileExtension: str = mediaType.split("/")[1]
        else:
            fileExtension = extension.get(mediaType, "bin")

        # Gera nome único para o arquivo
        if output is None:
            filename: str = f"{uuid.uuid4().hex}.{fileExtension}"
        else:
            filename = output

        output_path = os.path.join("static", filename)

        # Garante que a pasta static existe
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Salva o arquivo descriptografado
        with open(output_path, "wb") as f:
            f.write(data)

        # Gera a URL pública usando o ngrok
        public_url = f"{ngrok_url}/static/{filename}"
        return public_url

    except Exception as e:
        raise Exception(f"Erro no decryptByLink: {str(e)}")


if __name__ == "__main__":
    fileName: bytes = rb"static\file.enc"
    link: str = ""
    mediaKey: bytes = base64.b64decode("NNHOZQjWdjNg/QEC1NTpUplIvlfgj11AcWGMQk1NWV4=")

    if decryptByName(fileName, mediaKey, "image/jpeg"):
        print("Decrypted (hopefully)")
