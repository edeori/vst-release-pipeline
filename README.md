# Moth Production — közös VST release workflow

Publikus, újrafelhasználható GitHub Actions workflow macOS és Windows telepítők építéséhez. Publikus és privát VST-repók egyaránt hívhatják. **A build, a naplók és az artifactok a hívó VST-repó Actions felületén jelennek meg.** Ez a repó csak a közös kódot tartalmazza; kiadási titkokat nem tárol.

## Felépítés

- Közös pipeline: `.github/workflows/vst-release.yml`, `workflow_call` belépési ponttal.
- Minden VST saját hívója: `.github/workflows/release.yml`.
- A hívó megadja a Shop termékazonosítóját és átadja a saját GitHub Secrets értékeit.
- Mindkét platform a hívó eseményhez tartozó változatlan `github.sha` forráscommitot építi. A közös helper scriptek külön, rögzített commitról érkeznek.
- A workflow nem tölti le más privát repó pluginforrását: minden hívó a saját `GITHUB_TOKEN` tokenjét használja.

## StringLife indítása

A **StringLife-VST → Actions → Release installers → Run workflow** felületen. A `publish` alapértelmezetten kikapcsolt: csak GitHub artifactok készülnek. Bekapcsolva mindkét build sikere után a publish job kézi jóváhagyásra vár. Egy `v*` tag push automatikusan buildet indít, de az éles feltöltés akkor is jóváhagyást igényel. Az Actions futásban: **Review deployments → production → Approve and deploy**. StringLife esetén a kijelölt jóváhagyó `edeori`; a saját maga által indított kiadást is jóváhagyhatja, admin bypass nincs engedélyezve.

Az artifactok 30 napig maradnak meg. A macOS csomag aláírt és notarizált, a Windows telepítő jelenleg nem Authenticode-aláírt. A két MinIO-objektum feltöltése nem atomi; részleges hiba esetén a publish jobot futtasd újra. Régi futás újraindítása felülírhat újabb kiadást.

## Új VST bekötése

1. A VST-ben legyen `ci/package-mac.sh` és `ci/package-windows.ps1`. Az `examples/` mintáit igazítsd a projekthez.
2. A Shopban állítsd be a termékazonosítót, a `release_repository` mezőt (`edeori/RepoName`), a `release_enabled` kapcsolót és a két állandó telepítő-URL-t. Engedélyezett útvonal: `downloads/plugins/<id>/mac/<név>.pkg` és `downloads/plugins/<id>/win/<név>.exe` (`apps/` is támogatott). Ponttal elválasztott verzió ne kerüljön a fájlnévbe. A terméket működő letöltések után publikáld.
3. Ezen a Macen, bejelentkezett `gh` CLI-vel és `mothstack` SSH-hozzáféréssel:

```sh
python3 scripts/register-product.py phaselock edeori/PhaseLock-VST --checkout ../PhaseLock-VST
```

A script ellenőrzi a helyi repót, az adaptereket és az élő Shop-registryt; beállítja a `production` environment kötelező jóváhagyójának a bejelentkezett GitHub-felhasználót; létrehoz egy termékre korlátozott MinIO-felhasználót; beállítja a **VST-repó** secrets értékeit; és létrehozza annak `.github/workflows/release.yml` fájlját, teljes commit SHA-val rögzített közös workflow-hivatkozással. A meglévő eltérő hívófájlt nem írja felül. A Shop adatait nem módosítja. Regisztrációt ne futtass aktív kiadás közben, mert a MinIO-hozzáférést cseréli.

4. Nézd át, commitold és pushold a hívófájlt és az adaptereket **a VST-repóban**, majd ott indíts tesztet az Actions felületen.

A közös workflow frissítésekor a hívó `uses:` sorában kell az új, ellenőrzött commit SHA-ra váltani. Egy központi módosítás így nem változtatja meg váratlanul az összes VST kiadását.

## Adapterek szerződése

- Munkakönyvtár: a VST forrásrepójának gyökere.
- Mac: `bash ci/package-mac.sh` → nem üres `dist/installer.pkg`. A workflow importálja a tanúsítványokat és beállítja a `NOTARY_PROFILE=ci-notary` értéket. A projekt csomagolója ezzel írja alá, notarizálja és staplingeli a telepítőt; ezt a közös workflow utána ellenőrzi.
- Windows: `pwsh ci/package-windows.ps1` → nem üres `dist/installer.exe`. Az adapter ellenőrizze minden natív parancs hibakódját. A projekt Inno Setup sablonját külön biztosítani kell.
- A JUCE-target neve, licensing kapcsoló, buildprofil és telepítőstruktúra projektenként változhat; ezeket az adapterek kezelik.
- Más privát repóban lévő submodule/dependency külön olvasási hozzáférést igényel.

## Titkok és helyi beállítás

Minden hívó VST-repóban szükséges: `REGISTRY_TOKEN`, `APPLE_CERTIFICATES_P12`, `APPLE_CERTIFICATES_PASSWORD`, `APPLE_ID`, `APPLE_APP_PASSWORD`, `APPLE_TEAM_ID`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`. Opcionális repository variables: `CODESIGN_IDENTITY`, `INSTALLER_IDENTITY`.

Ezen a Macen a közös Apple-beállítás a login Kulcskarikában, `moth-vst-release-ci` szolgáltatásnéven található. A regisztráló script innen olvassa és közvetlenül a célrepó Secrets beállításaiba tölti fel. A jelszavakat nem írja a gitbe vagy a konzolra. A `moth-notary` helyi notarizációs profilt nem módosítja.

Új Macen exportáld a Developer ID Application és Installer tanúsítványokat a privát kulcsaikkal együtt egy jelszóvédett P12 fájlba, majd:

```sh
python3 scripts/setup-apple.py --p12 /biztonsagos/hely/signing.p12 --apple-id YOUR_APPLE_ID --team-id YOUR_TEAM_ID
```

A script rejtetten bekéri a P12-jelszót és az Apple app-jelszót, ellenőrzi a notarizációs hozzáférést és a helyi Kulcskarikába ment. Apple app-jelszó cseréjekor a már beállított Macen:

```sh
python3 scripts/setup-apple.py --repository edeori/StringLife-VST --repository edeori/PhaseLock-VST
```

## Ellenőrzés

```sh
PYTHONPATH=scripts python3 -m unittest discover -s tests
bash -n scripts/apple-signing.sh examples/package-mac.sh
```

A reusable workflow Node.js 24-alapú actionöket használ: checkout 7.0.1, upload-artifact 7.0.2, download-artifact 8.0.2. A korábbi központi teszt 2026-10-19-én mindkét platformon sikeres volt; az átállás utáni teszt már a StringLife Actions felületén fut.

2026-10-19: a [StringLife saját Actions-futása](https://github.com/edeori/StringLife-VST/actions/runs/39251229057) a publikus reusable workflow-val sikeres. Mindkét platform telepítője elkészült, a macOS aláírás és notarizáció ellenőrzése sikeres, a korábbi Node.js 20-as figyelmeztetés megszűnt (csak macOS runner-kapacitásról szóló tájékoztató notice maradt). Az éles MinIO-publikálás ki volt kapcsolva.

## Publikálási jóváhagyás és privát repók

A közös workflow publish jobja a hívó repó `production` environmentjét használja. Az environment nevének megadása önmagában nem jelent védelmet: kötelező reviewer-szabály is szükséges. A regisztráló script ezt létrehozza és ellenőrzi, hibánál leáll.

GitHub Free/Pro/Team csomagokban a required reviewers védelem csak publikus repókhoz érhető el. Privát repóknál az előfizetés támogatását külön ellenőrizni kell; enélkül külön manuális publikáló workflow szükséges, nem szabad védtelen environmenttel helyettesíteni a jóváhagyást. A privát repók közös buildje ettől függetlenül működhet. Lásd: https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments .
