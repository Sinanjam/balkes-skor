# TFF Factory v3.5 Dispatch Chain

v3.4 ilk grubu bitirdikten sonra `.github/tff-chain-v34-trigger.json` dosyasını GitHub Actions `GITHUB_TOKEN` ile pushluyordu. GitHub, `GITHUB_TOKEN` ile yapılan normal push olaylarından yeni workflow çalıştırmayı tetiklemez. Bu yüzden ilk grup `success` olsa bile ikinci grup başlamayabiliyordu.

v3.5 çözümü:

- İlk grup yine kullanıcı push'u ile `.github/tff-chain-v35-trigger.json` üzerinden başlar.
- Sonraki gruplar dosya push'u ile değil, `repository_dispatch` olayıyla başlatılır.
- `repository_dispatch`, `GITHUB_TOKEN` ile tetiklenebilen güvenli zincirleme yoludur.
- Empty manifest / 0 maç safety gate korunur.
- Data üretimi v3.4'ün doğruluk mantığını korur; zincirleme mekanizması v3.5'e yükselir.

Başlatma:

```fish
fish start_v35_chain.fish
```

İzleme:

```fish
gh run list --workflow tff_factory_chain_v35_dispatch.yml --limit 10
```
