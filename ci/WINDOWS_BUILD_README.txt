PyLaia 1.2.2+fork.20261014 — privat Windows-bygg
Versjon 1.2.2+fork.20261014. Dette er ikke den offisielle PyLaia-utgaven.

En målrettet Windows-retting rydder PyTorchs cuDNN-dropout-cache ved avslutning,
før GPU-bibliotekene lukkes. Den unngår et gjenskapt avslutningskrasj.
Ved GPU-bruk på 3.13/3.14 er cuDNN fortsatt aktivert. Dropout/modellinnstillinger endres ikke.
Ingen PyTorch- eller cuDNN-filer erstattes, og ingen feilstatus skjules.

Innhold:
- Opprinnelig pakkenavn pylaia, import laia og pylaia-htr-* kommandoer.
- Versjonsnummeret skiller bygget fra offisiell PyLaia.
- NumPy oppdatert fra 2.5.3 til 2.5.4; pakkenavn og kommandoer er uendret.
- Python 3.15.0, 3.14.8 og 3.13.16, kun brukt i et isolert miljø.
- Python 3.15 støttes med CPU på Windows; GPU beholdes på 3.13 og 3.14.
- Ferdigbygde Flashlight 0.0.7+pylaia1 og KenLM 0.3.0+pylaia1 for alle tre.
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

Standard er Python 3.14. For Python 3.13, legg til -PythonVersion 3.13.
For Python 3.15 med CPU:
   .\Install-PyLaia.ps1 -PythonVersion 3.15 -TorchBuild CPU
Uten -TorchBuild velger installasjonsprogrammet CUDA.
Installasjonen oppretter pylaia-env-3.14 (eller valgt 3.13/3.15) ved siden av denne filen.
Eksisterende installasjonsmapper overskrives ikke. Du kan velge -InstallationPath.
Ingen global Python, filtilknytning eller system-PATH endres.

Flashlight og KenLM installeres fra filene i pakken. De lastes ikke ned fra nettet.
PyTorch 2.14.1, TorchVision 0.29.1 og andre vanlige avhengigheter lastes ned fra
offisielle PyTorch/PyPI-kilder. Internettilgang trengs under denne første installasjonen.
Dette er altså ikke en fullstendig offlinepakke.
Ved CUDA-installasjon kreves en NVIDIA-driver som støtter CUDA 13.0.
Python 3.15 + CUDA avvises før installasjonen: begge testede offisielle CUDA-bygg
av PyTorch 2.14.1 har et avslutningskrasj i autograd-tråder. Distribuert kjøring
med Gloo/DDP på Windows 3.15 har også et kjent krasj og støttes ikke her.
Bruk 3.13/3.14 for GPU; på 3.15 brukes CPU, devices=1 og strategy=auto.
TorchAudio brukes fortsatt på 3.13/3.14. På 3.15 brukes samme Flashlight/KenLM
via en medfølgende adapter. Original TorchAudio-lisens følger med.

Installasjonen kontrollerer lokale filers kontrollsummer, avhengigheter, språkmodell-
dekoding og (ved CUDA) at grafikkortet faktisk kan brukes.

Etter installasjon:
  .\pylaia-env-3.14\Scripts\pylaia-htr-create-model.exe --version
  .\pylaia-env-3.14\Scripts\pylaia-htr-create-model.exe --help

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
