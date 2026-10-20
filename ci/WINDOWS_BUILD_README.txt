PyLaia 1.2.8+fork.20261020 — privat Windows-bygg
Versjon 1.2.8+fork.20261020. Dette er ikke den offisielle PyLaia-utgaven.

En målrettet Windows-retting rydder PyTorchs cuDNN-dropout-cache ved avslutning,
før GPU-bibliotekene lukkes. Den unngår et gjenskapt avslutningskrasj.
cuDNN er fortsatt aktivert på alle GPU-oppsett. Dropout/modellinnstillinger endres ikke.
For Python 3.15 følger egne PyTorch-bindinger kompilert mot korrekte Python-hoder.
Offisielle beregningsbiblioteker og CUDA/cuDNN-DLL-er beholdes uendret.

Innhold:
- Opprinnelig pakkenavn pylaia, import laia og pylaia-htr-* kommandoer.
- Versjonsnummeret skiller bygget fra offisiell PyLaia.
- Pillow 13.0.0 med nye sikkerhetsrettinger, filelock 4.2.4 og NumPy 2.5.4.
- python-bidi 0.6.12, setuptools 84.2.0 og installasjonsverktøyet pip 26.2.2.
- Valgfri W&B-logging bruker 0.31.0+pylaia1. Utviklingstester bruker Ruff 0.17.1 og tox 4.67.1.
- Testverktøy: cachetools 7.2.4, distlib 0.4.4, platformdirs 4.13.5, pluggy 1.7.0,
  pyproject-api 1.12.0, python-discovery 1.6.4 og virtualenv 21.14.11.
- Oppdatert testmiljø: Markdown 3.11.2, certifi 2026.10.19, xxhash 4.0.2 og wcwidth 0.9.3.
- Lokal SymPy 1.14.0+pylaia1 med mpmath 1.4.1 er inkludert.
- Lokal W&B 0.31.0+pylaia1 med cwevals 0.0.1b2 er inkludert, men er valgfri.
- Python 3.15.0 og 3.14.8, kun brukt i et isolert miljø. Python 3.13 er ikke støttet.
- Python 3.15 støttes med CPU og én NVIDIA-GPU; 3.14 beholdes også.
- Ferdige, korrigerte PyTorch 2.14.1-bindinger for 3.15 CPU/CUDA 13.2.
- Ferdigbygde Flashlight 0.0.7+pylaia1 og KenLM 0.3.0+pylaia1 for begge versjoner.
- Ferdigbygget python-bidi og PyYAML for 3.15; sluttbrukeren trenger ingen kompilator.
- Endret kildekode og opprinnelige lisenser i sources/, samt byggeverktøy.
- Kontrollsummer og byggeinformasjon i build-info.json.

Installasjon:
1. Pakk ut hele ZIP-filen. Ikke kjør installasjonen direkte fra ZIP-visningen.
2. Åpne PowerShell i mappen med denne filen.
3. Med NVIDIA-grafikkort og oppdatert driver:
   .\Install-PyLaia.ps1 -TorchBuild CUDA
   Uten NVIDIA-grafikkort:
   .\Install-PyLaia.ps1 -TorchBuild CPU

Standard er Python 3.15. For 3.14, legg til -PythonVersion 3.14.
For valgfri W&B-logging, legg til -WithWandb. De lokale hjulene ligger i compatibility/.
For Python 3.15 med CPU:
   .\Install-PyLaia.ps1 -PythonVersion 3.15 -TorchBuild CPU
Uten -TorchBuild velger installasjonsprogrammet CUDA.
Installasjonen oppretter pylaia-env-3.15 (eller valgt 3.14) ved siden av denne filen.
Eksisterende installasjonsmapper overskrives ikke. Du kan velge -InstallationPath.
Ingen global Python, filtilknytning eller system-PATH endres.

Flashlight og KenLM installeres fra filene i pakken. De lastes ikke ned fra nettet.
PyTorch 2.14.1, TorchVision 0.29.1 og andre vanlige avhengigheter lastes ned fra
offisielle PyTorch/PyPI-kilder. På 3.15 settes en vanlig PyTorch-wheel sammen fra
SHA-256-kontrollerte offisielle filer og de medfølgende, korrigerte bindingene.
Bruk -OriginalTorchWheel med en allerede nedlastet offisiell cp315-wheel om ønskelig.
Internettilgang trengs for de øvrige avhengighetene under den første installasjonen.
Dette er altså ikke en fullstendig offlinepakke.
Ved CUDA-installasjon kreves en NVIDIA-driver som støtter CUDA 13.2 på 3.15,
eller CUDA 13.0 på 3.14. Ikke installer de ukorrigerte offisielle cp315-pakkene
direkte: både CPU- og GPU-bindingene har en Python-ABI-feil. De nye bindingene
retter dette uten å slå av cuDNN. Bruk devices=1 og strategy=auto på 3.15.
Distribuert/multi-device-kjøring på Windows 3.15 er fortsatt ikke validert og
avvises. Bruk 3.14 til distribuert trening. torch.compile på 3.15 og
fri-trådet Python støttes ikke av denne utgaven.
TorchAudio brukes fortsatt på 3.14. På 3.15 brukes samme Flashlight/KenLM
via en medfølgende adapter. Original TorchAudio-lisens følger med.

Installasjonen kontrollerer lokale filers kontrollsummer, avhengigheter, språkmodell-
dekoding, autograd-tilbakekall, normal prosessavslutning og (ved CUDA) GPU/cuDNN.

Etter installasjon:
  .\pylaia-env-3.15\Scripts\pylaia-htr-create-model.exe --version
  .\pylaia-env-3.15\Scripts\pylaia-htr-create-model.exe --help

Andre kommandoer: pylaia-htr-train-ctc, pylaia-htr-decode-ctc,
pylaia-htr-netout og pylaia-htr-dataset-validate.
Ikke installer dette bygget og offisiell PyLaia i samme Python-miljø.
Gamle versjonskrav, treningsinnstillinger og modellfiler kan trenge tilpasning.
Dette er et kommandolinjeverktøy, ikke en ny grafisk OCR-app.

Modellfiler fra ukjente kilder bør ikke brukes. Tryggere innlasting er standard.
--common.allow_unsafe_pickle=true er kun for fullt betrodde gamle modellfiler;
det åpner for kjøring av Python-kode fra filen. Les SECURITY.md.

Bygging av tilleggene på nytt fra prosjektets Git-klone:
  .\ci\build-language-model.ps1 -Python .\.venv314\Scripts\python.exe -Install
MSVC x64 Build Tools og Windows SDK kreves bare ved ny kompilering, ikke for
bruk av de ferdigbygde pakkene. Ny bygging av python-bidi for 3.15 krever også
Rust/Cargo. Kontrollsummene er en integritetskontroll;
ZIP-filen er ikke kode-signert. Sammenlign også den separate ZIP-kontrollsummen.
Oppskrift for PyTorch-bindingene følger i build-tools/PYTORCH315_BUILD.md.
De lokale SymPy/W&B-variantene er versjonsmerket og har eksakte nye avhengighetskrav.
Numerisk kode og W&Bs native backend er uendret; kildearkiver, lisenser og oppskrift
følger med. cwevals er fortsatt beta. Sky-/kontoendepunkter er ikke testet live.
