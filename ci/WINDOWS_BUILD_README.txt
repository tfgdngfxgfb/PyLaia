PyLaia 1.2.3+fork.20261014 — privat Windows-bygg
Versjon 1.2.3+fork.20261014. Dette er ikke den offisielle PyLaia-utgaven.

En målrettet Windows-retting rydder PyTorchs cuDNN-dropout-cache ved avslutning,
før GPU-bibliotekene lukkes. Den unngår et gjenskapt avslutningskrasj.
cuDNN er fortsatt aktivert på alle GPU-oppsett. Dropout/modellinnstillinger endres ikke.
For Python 3.15 følger egne PyTorch-bindinger kompilert mot korrekte Python-hoder.
Offisielle beregningsbiblioteker og CUDA/cuDNN-DLL-er beholdes uendret.

Innhold:
- Opprinnelig pakkenavn pylaia, import laia og pylaia-htr-* kommandoer.
- Versjonsnummeret skiller bygget fra offisiell PyLaia.
- NumPy oppdatert fra 2.5.3 til 2.5.4; pakkenavn og kommandoer er uendret.
- Python 3.15.0, 3.14.8 og 3.13.16, kun brukt i et isolert miljø.
- Python 3.15 støttes med CPU og én NVIDIA-GPU; 3.13/3.14 beholdes også.
- Ferdige, korrigerte PyTorch 2.14.1-bindinger for 3.15 CPU/CUDA 13.2.
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

Standard er Python 3.15. For 3.13/3.14, legg til -PythonVersion 3.13 eller 3.14.
For Python 3.15 med CPU:
   .\Install-PyLaia.ps1 -PythonVersion 3.15 -TorchBuild CPU
Uten -TorchBuild velger installasjonsprogrammet CUDA.
Installasjonen oppretter pylaia-env-3.15 (eller valgt 3.13/3.14) ved siden av denne filen.
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
eller CUDA 13.0 på 3.13/3.14. Ikke installer de ukorrigerte offisielle cp315-pakkene
direkte: både CPU- og GPU-bindingene har en Python-ABI-feil. De nye bindingene
retter dette uten å slå av cuDNN. Bruk devices=1 og strategy=auto på 3.15.
Distribuert/multi-device-kjøring på Windows 3.15 er fortsatt ikke validert og
avvises. Bruk 3.13/3.14 til distribuert trening. torch.compile på 3.15 og
fri-trådet Python støttes ikke av denne utgaven.
TorchAudio brukes fortsatt på 3.13/3.14. På 3.15 brukes samme Flashlight/KenLM
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
mpmath beholdes på 1.3.0 fordi nyeste SymPy krever en versjon under 1.4.
