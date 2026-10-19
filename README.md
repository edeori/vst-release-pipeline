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

## Windows Defender ellenőrzés

A Windows csomagolás után kötelező Defender-vizsgálat fut a teljes forrás- és buildkönyvtáron, beleértve a kicsomagolt pluginbinárisokat és a végleges telepítőt. A script frissíti a vírusadatbázist, ellenőrzi az aktív antivírust és az adatbázis frissességét (legfeljebb 48 óra). A custom scan figyelmen kívül hagyja a kizárásokat, archívumokat is vizsgál, és nem végez automatikus javítást. Találat, frissítési hiba, hiányzó Defender vagy időtúllépés blokkolja a telepítő artifactját és a publikálást.

A `defender-<termék>-windows` artifact tartalmazza az eredményt, a motor/adatbázis verzióját, az EXE SHA-256 értékét és a vizsgálat kimenetét. Az ellenőrzés nem jelent Microsoft-jóváhagyást vagy SmartScreen-reputációt; a Windows-telepítő továbbra is aláíratlan.

A `Test Defender scanner` kézzel indítható karbantartási workflow a már publikált StringLife EXE-vel ellenőrzi a scannert, majd egy ártalmatlan EICAR tesztfájllal igazolja a blokkolást. Nem publikál és nem használ kiadási titkokat. A normál VST-build továbbra is a VST saját Actions felületén fut.

2026-10-19: a [scanner integrációs tesztje](https://github.com/edeori/vst-release-pipeline/actions/runs/39255915956) sikeres: a publikált EXE tiszta, az EICAR-tesztfájl `Virus:DOS/EICAR_Test_File` észlelést és blokkoló 2-es kilépési kódot adott. A GitHub runneren tapasztalt PowerShell `Update-MpSignature` RPC-hiba miatt a frissítés a natív `MpCmdRun -SignatureUpdate -MMPC` parancsot használja, legfeljebb három próbálkozással.

A [StringLife teljes buildtesztjének](https://github.com/edeori/StringLife-VST/actions/runs/39255855252) Windows-jobja sikeres: a frissen fordított plugin és telepítő teljes buildkönyvtárának vizsgálata 20 másodperc alatt, találat nélkül lefutott. A teszt `publish=false` beállítással indult.

## Külön kézi publikálás privát repókban

A `register-product.py` `--publication-mode separate` kapcsolója két hívót hoz létre a VST-repóban: `release.yml` (Build installers) és `publish.yml` (Publish installers). A build mindig `publish: false`, és nem kap MinIO-titkokat. A Publish csak kézzel, a repó alapértelmezett ágáról indítható; indítása maga a kiadási jóváhagyás, nincs environment gate.

A Publish `build_run_id` mezője a korábbi sikeres Build installers futás száma. A közös `vst-publish.yml` ellenőrzi a forrásrepót, a workflow-azonosítót, a futás sikerességét és az EXE egyezését a tiszta Defender-jelentéssel. Ugyanannak a futásnak a telepítőit tölti fel újrafordítás nélkül. A `verify_only` kapcsoló minden ellenőrzést és letöltést elvégez, de nem ír a MinIO-ra. Lejárt artifactból nem lehet publikálni. Régi sikeres futás kiválasztása szándékos visszaállítást tesz lehetővé.

```sh
python3 scripts/register-product.py deathwings edeori/DeathWings-VST --checkout ../DeathWings-VST --publication-mode separate
```

A StringLife meglévő environment-jóváhagyásos működése változatlan. A DeathWings a külön publikálási módot használja és privát marad.

## Legutóbbi sikeres build kiválasztása

A külön Publish hívók `build_selection` legördülője alapértelmezetten **Latest successful build**. A `build_run_id` ilyenkor üres marad. A közös validator a hívó repo alapértelmezett ágának legutóbb létrehozott sikeres `release.yml` futását választja, PR-futások nélkül. Régi build újrafuttatása nem teszi azt a legújabbá. A kiválasztás végrehajtáskor történik; az egyszer feloldott futásazonosítót használja minden artifactletöltés és az eredményösszesítő. Hiányzó/lejárt artifact esetén nincs automatikus visszalépés korábbi buildre.

A **Specific build ID** opcióval konkrét korábbi vagy tagről készült build is kiválasztható. A `verify_only` mindkét móddal működik. Az új opció bekötve: DeathWings, WhammyDT/WhirlDT és Swarm. A regisztráló script új külön Publish workflow-kat is ezzel a felülettel generál. A StringLife meglévő, egy workflow-n belüli jóváhagyásos publikálása nem változott.

## Automatic build versions

New default-branch pushes and manual branch builds reserve the next CMake
`project(... VERSION major.minor.patch)` patch number before either platform
builds. The reservation is a GitHub Actions bot commit in the source branch;
macOS and Windows both check out that exact commit. Callers grant contents:write,
but only the prepare job writes source. Build jobs retain read permissions.

Each run reserves `ci-build/<run-id>` atomically with its version commit. A rerun
reuses that reservation, including after a failed build; patch numbers consumed
by failed builds are not recycled. Bot commits include [skip ci], and token pushes
do not recursively start another workflow. If the branch has advanced before
reservation, the old run fails safely; start from the current branch. Concurrent
pushes are never force-overwritten. Pull remote bot commits before further local
pushes; do not discard unrelated local work to synchronize.

Explicit `vMAJOR.MINOR.PATCH` tag builds keep their version and require the tag to
match CMake exactly. They do not bump or move the release tag. Publish never bumps.
In legacy gated mode only tag pushes request publication automatically; ordinary
branch pushes build only. Separate Publish remains manual.

A release-metadata artifact records trigger SHA, built SHA, version and run ID.
Publish validates its binding and checks the version commit only changed
CMakeLists.txt, then reports the actual source SHA. Older builds without metadata
remain publishable using their original source SHA. Expired metadata fails.

Automatic-version integration verified on 2026-10-19 using ParaDyn EQ:
[build 39305139718](https://github.com/edeori/parametric-dynamic-eq-VST/actions/runs/39305139718)
reserved 0.1.2 in commit `35235e3ade46bc4d1050a6296d3bcc385c1eda0a`.
Both platforms passed, including licensing checks, Apple notarization and Defender.
Downloaded Windows ProductVersion, Mac package version and all three Mac bundle
versions were checked as 0.1.2.
[Publish verification 39305375515](https://github.com/edeori/parametric-dynamic-eq-VST/actions/runs/39305375515)
validated the reserved commit/version and both installers; live upload was skipped.
