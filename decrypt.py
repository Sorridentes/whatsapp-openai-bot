from Crypto.Cipher import AES
from Crypto.Cipher._mode_cbc import CbcMode
from typing import Optional
from config import Config
import logging
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

logger: logging.Logger = logging.getLogger(__name__)


def _HKDF(key: bytes, length: int, appInfo: bytes = b"") -> bytes:
    logger.debug(f"Iniciando HKDF - length: {length}, appInfo: {appInfo}")
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
    logger.debug(f"HKDF concluído - keyStream length: {len(keyStream)}")
    return keyStream[:length]


def _AESUnpad(s: bytes) -> bytes:
    logger.debug(f"Iniciando AESUnpad - input length: {len(s)}")
    result = s[: -ord(s[len(s) - 1 :])]
    logger.debug(f"AESUnpad concluído - output length: {len(result)}")
    return result


def _AESDecrypt(key: bytes, ciphertext: bytes, iv: Optional[bytes]) -> bytes:
    logger.debug(
        f"Iniciando AESDecrypt - key length: {len(key)}, ciphertext length: {len(ciphertext)}, iv length: {len(iv) if iv else 0}"
    )
    cipher: CbcMode = AES.new(key, AES.MODE_CBC, iv)  # type: ignore
    plaintext: bytes = cipher.decrypt(ciphertext)
    result = _AESUnpad(plaintext)
    logger.debug(f"AESDecrypt concluído - plaintext length: {len(result)}")
    return result


def decryptByName(
    fileName: bytes, mediaKey: bytes, mediaType: str, output: Optional[bytes] = None
) -> bool:
    logger.info(
        f"Iniciando descriptografia local - arquivo: {fileName}, tipo: {mediaType}"
    )

    try:
        mediaKeyExpanded = _HKDF(mediaKey, 112, appInfo[mediaType])

        with open(fileName, "rb") as f:
            mediaData = f.read()
        logger.debug(f"Arquivo lido: {len(mediaData)} bytes")

        file = mediaData[:-10]
        data = _AESDecrypt(mediaKeyExpanded[16:48], file, mediaKeyExpanded[:16])

        if output is None:
            if "/" in mediaType:
                fileExtension = mediaType.split("/")[1]
            else:
                fileExtension = extension[mediaType]
            output = fileName.replace(b".enc", f".{fileExtension}".encode("utf-8"))

        with open(output, "wb") as f:
            f.write(data)

        logger.info(f"Descriptografia concluída - arquivo salvo: {output}")
        return True

    except Exception as e:
        logger.error(f"Erro na descriptografia local: {str(e)}")
        return False


def decryptByLink(
    link: str,
    mediaKey: bytes,
    mediaType: str,
    ngrok_url: str = Config.NGROK_URL,
    output: Optional[str] = None,
) -> str:
    """
    Descriptografa arquivo do WhatsApp e retorna URL pública via ngrok
    """
    logger.info(f"Iniciando descriptografia por link - tipo: {mediaType}")

    try:
        logger.debug(f"Fazendo download de: {link}")
        response = requests.get(link, timeout=30)
        try:
            response.raise_for_status()
        except requests.HTTPError:
            logger.warning(f"Erro HTTP {response.status_code} ao baixar arquivo")
            raise requests.HTTPError(
                f"Erro HTTP {response.status_code} ao baixar arquivo"
            )

        mediaData = response.content
        logger.debug(f"Download concluído: {len(mediaData)} bytes")

        mediaKeyExpanded = _HKDF(mediaKey, 112, appInfo[mediaType])
        file = mediaData[:-10]
        data = _AESDecrypt(mediaKeyExpanded[16:48], file, mediaKeyExpanded[:16])

        # Determina extensão do arquivo
        if "/" in mediaType:
            fileExtension = mediaType.split("/")[1]
        else:
            fileExtension = extension.get(mediaType, "bin")

        # Gera nome único para o arquivo
        if output is None:
            filename = f"{uuid.uuid4().hex}.{fileExtension}"
        else:
            filename = output

        output_path = os.path.join("static", filename)

        # Garante que a pasta static existe
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Salva o arquivo descriptografado
        with open(output_path, "wb") as f:
            f.write(data)
        logger.debug(f"Arquivo salvo: {output_path}")

        # Gera a URL pública usando o ngrok
        public_url = f"{ngrok_url}/static/{filename}"
        logger.info(f"Descriptografia por link concluída - URL: {public_url}")

        return public_url
    except requests.HTTPError as e:
        raise e
    except Exception as e:
        logger.error(f"Erro na descriptografia por link: {str(e)}")
        raise Exception(f"Erro no decryptByLink: {str(e)}")


if __name__ == "__main__":
    fileName: bytes = rb"static\file.enc"
    link: str = ""
    mediaKey: bytes = base64.b64decode("NNHOZQjWdjNg/QEC1NTpUplIvlfgj11AcWGMQk1NWV4=")

    if decryptByName(fileName, mediaKey, "image/jpeg"):
        print("Decrypted (hopefully)")
