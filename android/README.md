# Нора для Android (Google Play, RuStore)

Оболочка Trusted Web Activity: открывает https://nora-books.ru/app.html?app=1&src=android.
Правки приложения по-прежнему делаются в app-dev.html - в Android-версии они появляются сами, без новой загрузки в магазин.
Новая сборка нужна только при смене иконки, названия, адреса или версии Android.

- Пакет: ru.norabooks.app
- Сборка: GitHub Actions «Android» (.github/workflows/android.yml) - собирает НЕподписанные app-release.aab и app-release.apk.
- Подпись: ключ загрузки nora-upload.jks (alias nora) хранится у владелицы, в репозиторий его класть нельзя.
  AAB: jarsigner -keystore nora-upload.jks app-release.aab nora
  APK: java -jar apksigner.jar sign --ks nora-upload.jks --ks-key-alias nora app-release.apk (apksigner.jar лежит в той же сборке)
- Связь сайта и приложения: /.well-known/assetlinks.json (отпечаток SHA-256 ключа загрузки и, после первой загрузки в Play, ключа подписи Google из Play Console -> Целостность приложения).
- В приложении из магазина (src=android) не показываются клубы с ведущими и «Сотрудничество» - оплату цифрового магазины разрешают только через свои платежи.
