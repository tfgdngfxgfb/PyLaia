PyLaia 1.2.12+fork.20261107 — privat Windows-bygg
Versjon 1.2.12+fork.20261107. Dette er ikke den offisielle PyLaia-utgaven.

En målrettet Windows-retting rydder PyTorchs cuDNN-dropout-cache ved avslutning,
før GPU-bibliotekene lukkes. Den unngår et gjenskapt avslutningskrasj.
cuDNN er fortsatt aktivert på alle GPU-oppsett. Dropout/modellinnstillinger endres ikke.
Python 3.15 bruker offisielle PyTorch 2.15.0-bindinger uten lokale
DLL-endringer. De tidligere bindingene for PyTorch 2.14.1 brukes ikke i dette bygget.
Python 3.15 testes lokalt på CPU og GPU. GitHub CI tester på CPU.

Innhold:
- Opprinnelig pakkenavn pylaia, import laia og pylaia-htr-* kommandoer.
- Versjonsnummeret skiller bygget fra offisiell PyLaia.
- Pillow 13.0.0 med nye sikkerhetsrettinger, filelock 4.2.9 og NumPy 2.5.4.
- python-bidi 0.6.12, setuptools 84.2.1 og installasjonsverktøyet pip 26.3.
- jsonargparse 4.53.0. Valgfri W&B-logging bruker 0.31.0+pylaia2.
- Utviklingstester bruker pytest 9.2.0, Ruff 0.17.4 og tox 4.67.13.
- Testverktøy: cachetools 8.0.0, distlib 0.4.4, platformdirs 4.14.5, pluggy 1.7.0,
  pyproject-api 1.12.5, python-discovery 1.9.5 og virtualenv 21.15.6.
- Oppdatert testmiljø: Markdown 3.11.3, certifi 2026.10.23, xxhash 4.0.2 og wcwidth 0.9.4.
- Lokal SymPy 1.14.0+pylaia1 med mpmath 1.4.1 er inkludert.
- Lokal W&B 0.31.0+pylaia2 med cwevals 0.0.1b3 er inkludert, men er valgfri.
- Python 3.15 i et isolert miljø med CPU eller én NVIDIA-GPU.
- SHA256-pinnet installasjon av offisiell PyTorch 2.15.0 og TorchVision 0.29.2.
- CPU og CUDA 13.2 på Python 3.15, uten egne Torch-bindinger.
- Ferdigbygde Flashlight 0.0.7+pylaia1 og KenLM 0.3.0+pylaia1.
- Offisielt python-bidi-hjul og ferdigbygget PyYAML for 3.15.
- Endret kildekode og opprinnelige lisenser i sources/, samt byggeverktøy.
- Kontrollsummer og byggeinformasjon i build-info.json.

Installasjon:
1. Pakk ut hele ZIP-filen. Ikke kjør installasjonen direkte fra ZIP-visningen.
2. Åpne PowerShell i mappen med denne filen.
3. Med NVIDIA-grafikkort og oppdatert driver:
   .\Install-PyLaia.ps1 -TorchBuild CUDA
   Uten NVIDIA-grafikkort:
   .\Install-PyLaia.ps1 -TorchBuild CPU

For valgfri W&B-logging, legg til -WithWandb. De lokale hjulene ligger i compatibility/.
For Python 3.15 med CPU:
   .\Install-PyLaia.ps1 -PythonVersion 3.15 -TorchBuild CPU
Uten -TorchBuild velger installasjonsprogrammet CUDA.
Installasjonen oppretter pylaia-env-3.15 ved siden av denne filen.
Eksisterende installasjonsmapper overskrives ikke. Du kan velge -InstallationPath.
Ingen global Python, filtilknytning eller system-PATH endres.

Flashlight og KenLM installeres fra filene i pakken. De lastes ikke ned fra nettet.
PyTorch 2.15.0, TorchVision 0.29.2 og andre vanlige avhengigheter lastes ned fra
offisielle PyTorch/PyPI-kilder. Torch-/TorchVision-hjulenes SHA256 kontrolleres.
Ingen Torch-bindinger byttes ut eller kompileres lokalt.
Bruk -OriginalTorchWheel med et allerede nedlastet offisielt Torch-hjul om ønskelig;
kontrollsummen må passe valgt Python-versjon og CPU-/CUDA-profil.
Internettilgang trengs for de øvrige avhengighetene under den første installasjonen.
Dette er altså ikke en fullstendig offlinepakke.
Ved CUDA-installasjon kreves en NVIDIA-driver som støtter CUDA 13.2 på Python 3.15. CUDA Toolkit og kompilator trenger ikke installeres.
cuDNN forblir aktivert. Bruk devices=1 og strategy=auto på 3.15.
Distribuert/multi-device-kjøring på Windows 3.15 er fortsatt ikke validert og
avvises. torch.compile og fri-trådet Python
er ikke kvalifisert av denne utgaven; den vanlige PyLaia-arbeidsflyten bruker eager.
Språkmodelldekoding bruker Flashlight/KenLM via en medfølgende adapter. Original TorchAudio-lisens følger med.

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
  .\ci\build-language-model.ps1 -Python .\.venv315\Scripts\python.exe -Install
MSVC x64 Build Tools og Windows SDK kreves bare ved ny kompilering, ikke for
bruk av de ferdigbygde pakkene. Kontrollsummene verifiserer integriteten.
ZIP-filen er ikke kode-signert. Sammenlign også den separate ZIP-kontrollsummen.
Offisielle Torch-/TorchVision-adresser og kontrollsummer følger i
build-tools/torch215-wheels.json. Gamle bygg og deres bindingsoppskrifter er bevart
separat, men brukes ikke av denne installasjonen.
De lokale SymPy/W&B-variantene er versjonsmerket og har eksakte nye avhengighetskrav.
Numerisk kode og W&Bs native backend er uendret; kildearkiver, lisenser og oppskrift
følger med. cwevals er fortsatt beta. Sky-/kontoendepunkter er ikke testet live.
