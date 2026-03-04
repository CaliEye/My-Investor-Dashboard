(function () {
  const te = new TextEncoder();
  const td = new TextDecoder();

  function toBase64(bytes) {
    let binary = '';
    const chunk = 0x8000;
    for (let i = 0; i < bytes.length; i += chunk) {
      binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
    }
    return btoa(binary);
  }

  function fromBase64(value) {
    const binary = atob(value);
    const arr = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) {
      arr[i] = binary.charCodeAt(i);
    }
    return arr;
  }

  async function deriveAesKey(passphrase, salt) {
    const keyMaterial = await crypto.subtle.importKey(
      'raw',
      te.encode(passphrase),
      'PBKDF2',
      false,
      ['deriveKey']
    );

    return crypto.subtle.deriveKey(
      {
        name: 'PBKDF2',
        salt,
        iterations: 250000,
        hash: 'SHA-256'
      },
      keyMaterial,
      { name: 'AES-GCM', length: 256 },
      false,
      ['encrypt', 'decrypt']
    );
  }

  async function encryptObject(payload, passphrase) {
    const salt = crypto.getRandomValues(new Uint8Array(16));
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const key = await deriveAesKey(passphrase, salt);

    const ciphertext = await crypto.subtle.encrypt(
      { name: 'AES-GCM', iv },
      key,
      te.encode(JSON.stringify(payload))
    );

    return {
      version: 1,
      createdAt: new Date().toISOString(),
      salt: toBase64(salt),
      iv: toBase64(iv),
      ciphertext: toBase64(new Uint8Array(ciphertext))
    };
  }

  async function decryptObject(encryptedPayload, passphrase) {
    const salt = fromBase64(encryptedPayload.salt);
    const iv = fromBase64(encryptedPayload.iv);
    const ciphertext = fromBase64(encryptedPayload.ciphertext);
    const key = await deriveAesKey(passphrase, salt);

    const plaintext = await crypto.subtle.decrypt(
      { name: 'AES-GCM', iv },
      key,
      ciphertext
    );

    return JSON.parse(td.decode(plaintext));
  }

  async function exportEncryptedStorage(keys, passphrase, fileName) {
    const payload = {
      storage: {},
      metadata: {
        exportedAt: new Date().toISOString(),
        keys
      }
    };

    keys.forEach((key) => {
      payload.storage[key] = localStorage.getItem(key);
    });

    const encrypted = await encryptObject(payload, passphrase);
    const blob = new Blob([JSON.stringify(encrypted, null, 2)], { type: 'application/json' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = fileName || 'endgame-secure-backup.json';
    link.click();
    URL.revokeObjectURL(link.href);
  }

  async function importEncryptedStorage(file, passphrase) {
    const text = await file.text();
    const encryptedPayload = JSON.parse(text);
    const decrypted = await decryptObject(encryptedPayload, passphrase);

    Object.entries(decrypted.storage || {}).forEach(([key, value]) => {
      if (value === null || value === undefined) {
        localStorage.removeItem(key);
      } else {
        localStorage.setItem(key, value);
      }
    });

    return (decrypted.metadata && decrypted.metadata.keys) || [];
  }

  window.secureBackup = {
    exportEncryptedStorage,
    importEncryptedStorage
  };
})();