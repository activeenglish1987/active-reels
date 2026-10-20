# Video 01 — ElevenLabs seslendirme metni

## Ayarlar
- **Model:** Eleven v3 (köşeli parantezli duygu etiketlerini destekler). v3 yoksa Multilingual v2 kullan ve aşağıdaki **etiketsiz** metni yapıştır.
- **Ses:** Kütüphaneden doğal, sıcak, genç yetişkin Türkçe kadın sesi ("Turkish", "female", "conversational" filtreleri). Seçtiğin sesin adını buraya yaz, sonraki bölümlerde aynısını kullanacağız: `[ses adı]`
- **Stability:** 0,45 (v3'te "Natural") · **Similarity:** 0,80 · **Style:** 0,30 · **Speed:** 1,0
- **Çıktı:** MP3 44,1 kHz 192 kbps (ya da WAV). Tek dosya, tüm metin tek seferde.
- **Hedef süre:** 14–16 sn. Uzun çıkarsa Speed'i 1,05–1,1 yap.
- **Ticari kullanım:** Ücretli plan gerekli.

## Metin — Eleven v3 (etiketli)
Olduğu gibi kopyala. Köşeli parantezler okunmaz, ses tonunu yönlendirir.

```
[serious] Hapı yuttuk'u İngilizceye çevirdim.
[deadpan] We swallowed the pill.
[playful] Hayır. Doğrusu: We're done for.
[serious] Kafayı yedim: I ate the head.
[light laugh] Doğrusu: I've lost my mind.
[serious] Etekleri zil çalıyor: Her skirts are ringing bells.
[warmly] Doğrusu: She's over the moon.
[playful] Sıradakini sen yaz... yoksa hapı yuttuk.
```

## Metin — Multilingual v2 (etiketsiz)
```
Hapı yuttuk'u İngilizceye çevirdim.
We swallowed the pill.
Hayır. Doğrusu: We're done for.
Kafayı yedim: I ate the head.
Doğrusu: I've lost my mind.
Etekleri zil çalıyor: Her skirts are ringing bells.
Doğrusu: She's over the moon.
Sıradakini sen yaz... yoksa hapı yuttuk.
```

## Dinlerken kontrol et
- **İngilizce cümleler** anlaşılır mı? Özellikle *We're done for*, *I've lost my mind*, *She's over the moon*. Bozuksa yalnız o satırı yeniden üret (ElevenLabs'te satırı seçip "Regenerate").
- **"Hapı yuttuk'u"** doğal mı okunuyor? Garip olursa "Hapı yuttuk deyimini İngilizceye çevirdim." yaz (ekran yazısı aynı kalır, süre ~0,5 sn uzar).
- Satırlar arasında kısa duraklama olsun; uzun sessizlik olursa ben kurguda kısaltırım.

Dosyayı bu sohbete yükle; kartları cümlelere ben oturtacağım.
