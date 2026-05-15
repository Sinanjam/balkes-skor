# Firebase Active Users GitHub Action cache fix

Son hata `actions/setup-python@v5` adımında oluştu:

```text
No file ... matched to [**/requirements.txt or **/pyproject.toml]
```

Sebep: workflow içinde `cache: pip` açıktı, fakat repoda pip cache anahtarı çıkaracak `requirements.txt` veya `pyproject.toml` yoktu.

Bu patch:

- `cache: pip` satırını kaldırır.
- Firebase sayaç bağımlılığını ayrı `requirements-firebase-actions.txt` dosyasına taşır.
- Workflow `pip install -r requirements-firebase-actions.txt` ile kurulum yapar.

Bu workflow repo'ya commit/push yapmaz; sadece Firestore üzerinde `public_stats/app` dokümanını günceller. TFF veri çekme workflow'u ile aynı anda çalışması güvenlidir.
