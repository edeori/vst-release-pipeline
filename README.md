# Moth Production — központi VST build

Privát build-repó: a macOS és Windows kiadás itt fut, a pluginforrás másik, publikus vagy privát repóban maradhat. A `products.json` rendeli a Shop termékazonosítót a forrásrepóhoz. A workflow mindkét platformon ugyanazt a feloldott commitot építi.

## Build indítása

Actions → **Build VST installers** → Run workflow:

- `product`: például `stringlife`.
- `ref`: forráság, tag vagy commit SHA, például `main` vagy `v1.6.3`.
- `publish`: kikapcsolva tesztbuild; bekapcsolva mindkét sikeres build után éles MinIO-feltöltés.

Parancssorból, bejelentkezett GitHub CLI-vel:

```sh
python3 scripts/release.py stringlife --ref main
python3 scripts/release.py stringlife --ref v1.6.3 --publish
```

A tesztbuild telepítői 30 napig a központi Actions-futás artifactjai között maradnak. A Windows telepítő jelenleg nem Authenticode-aláírt. A macOS aláírt és notarizált. A két MinIO-feltöltés nem atomi; részleges hiba esetén ugyanannak a futásnak a publish jobját indítsd újra. Régi futás újraindítása felülírhat újabb kiadást.

## Új VST bekötése

1. A forrásrepóban legyen `ci/package-mac.sh` és `ci/package-windows.ps1`. A példák az `examples/` alatt indulási minták; a projektre kell igazítani őket. Commitold és pushold az adaptereket.
2. A Shopban állítsd be a termékazonosítót, a `release_repository` mezőt (`edeori/RepoName`), a `release_enabled` kapcsolót és a két állandó letöltési URL-t. A registry ellenőrzi a termékhez tartozó `plugins/<id>/mac/*.pkg`, `plugins/<id>/win/*.exe` útvonalakat (az `apps/` prefix is támogatott). A fájlnevekben ne legyen ponttal elválasztott verzió. A termék közzétételét csak a működő letöltések után végezd el.
3. Ezen a Macen, `gh` belépéssel és `mothstack` SSH-hozzáféréssel:

```sh
python3 scripts/register-product.py phaselock edeori/PhaseLock-VST
git add products.json
git commit -m 'Register PhaseLock release builds'
git push
python3 scripts/release.py phaselock
```

A regisztráló script előbb ellenőrzi az élő Shop-konfigurációt és az adaptereket. Ezután létrehozza a központi repó termékhez tartozó environmentjét, egy olvasási deploy keyt a forrásrepóhoz, és egy kizárólag a termék MinIO-prefixére jogosult felhasználót. Ismételt regisztráció lecseréli a hozzáféréseket; ne futtasd aktív kiadás közben. A Shop tartalmát nem írja át. A git commit/push külön lépés.

## Adapterek szerződése

- Munkakönyvtár: a forrásrepó gyökere.
- Mac: `bash ci/package-mac.sh` → nem üres `dist/installer.pkg`. `NOTARY_PROFILE=ci-notary` már be van állítva; a tanúsítványokat a központi workflow importálja. A projekt csomagolójának ezt a profilt kell használnia, a csomagot alá kell írnia és notarizálnia.
- Windows: `pwsh ci/package-windows.ps1` → nem üres `dist/installer.exe`. Minden natív parancs hibakódját ellenőrizze az adapter. Inno Setup a Windows runneren elérhető, de a projekt telepítősablonját külön kell biztosítani.
- A központi pipeline nem feltételezi a JUCE-target nevét, a licensing kapcsolót, a build profilját vagy az installer belső felépítését.
- A forrásrepó deploy keyje csak azt az egy repót olvassa. Másik privát repóban lévő submodule/dependency külön hozzáférést igényel.

## Hitelesítők

Központi repository secrets: `REGISTRY_TOKEN`, `APPLE_CERTIFICATES_P12`, `APPLE_CERTIFICATES_PASSWORD`, `APPLE_ID`, `APPLE_APP_PASSWORD`, `APPLE_TEAM_ID`.

Termékenkénti environment secrets: `SOURCE_SSH_KEY`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`. A forrásrepókban nem kell Apple- vagy MinIO-titkot tárolni. Opcionális központi variables: `CODESIGN_IDENTITY`, `INSTALLER_IDENTITY`.

A forráskód és adapterei a buildben aláírókulcsot használhatnak, ezért csak megbízható saját commitot építs. Tetszőleges külső repó nem adható meg a workflow bemenetében: a központilag commitolt terméklista és az élő Shop-registry egyezése szükséges.

## Ellenőrzés

```sh
PYTHONPATH=scripts python3 -m unittest discover -s tests
bash -n scripts/apple-signing.sh examples/package-mac.sh
```

A központi workflow manuálisan vagy a `scripts/release.py` parancsból indul. A forrásrepók tag-push eseménye önmagában nem indít központi buildet. Ehhez később külön, hitelesített indítót kell bekötni; a forrásrepó alapértelmezett `GITHUB_TOKEN` tokenje nem indíthat workflow-t ebben a másik privát repóban.

## Ellenőrzött első futás

2026-10-19: [StringLife központi tesztbuild](https://github.com/edeori/vst-release-pipeline/actions/runs/39248988586) sikeres. Forráscommit: `8543b16`, CMake-verzió: `1.6.2`. A registry és a forrásolvasás működött; a Windows `.exe` és a macOS `.pkg` artifact elkészült; a macOS aláírás és notarizáció ellenőrzése sikeres. A `publish` ki volt kapcsolva, ezért ez a futás nem cserélte le az éles MinIO-objektumokat.

Az Apple app-jelszó cseréjéhez ezen a Macen: `bash scripts/set-apple-password.sh`. A script rejtetten bekéri, Apple-nél ellenőrzi, majd közvetlenül a központi GitHub secretbe menti. A helyi `moth-notary` profilt nem módosítja.
