# TFF Factory v3.6 Compact Dispatch Chain

v3.6, v3.5 zincirindeki `repository_dispatch` payload sınırı hatasını düzeltir.

## Düzeltilen hata

GitHub `repository_dispatch` için `client_payload` içinde en fazla 10 üst-seviye property kabul eder. v3.5 tüm zincir ayarlarını üst seviyeye koyduğu için 18 property gönderiyor ve şu hatayı alıyordu:

```text
No more than 10 properties are allowed; 18 were supplied. (HTTP 422)
```

v3.6 tüm ayarları tek üst-seviye `config` objesinin içine alır:

```json
{
  "event_type": "tff-chain-v36",
  "client_payload": {
    "config": { "...": "..." },
    "meta": { "...": "..." }
  }
}
```

Böylece sonraki 4'lü grup otomatik tetiklenebilir.

## Devam başlatma

v3.5 ile `2021-2022..2018-2019` başarıyla yazıldıysa devam komutu:

```fish
fish start_v36_chain.fish 2017-2018 false
```

Baştan kurulum için:

```fish
fish start_v36_chain.fish 2025-2026 true
```
