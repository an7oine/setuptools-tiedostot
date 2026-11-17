# -*- coding: utf-8 -*-

import hashlib
import os
from pathlib import Path, PurePosixPath
import tempfile
import zipfile

try:
  import tomllib
except ModuleNotFoundError:
  import tomli as tomllib

from setuptools.errors import SetupError

# Prosessin sisäinen välimuisti: `python -m build` ajaa egg_info-
# kirjoittimen useita kertoja, usein erillisissä prosesseissa.
_LISTAUS_VALIMUISTI: dict[tuple[str, ...], list[str]] = {}


def kirjoita_asennetut_tiedostot(cmd, basename, filename):
  '''
  Kirjoita riippuvuuswheelien tiedostopolut egg-info-metadataan.
  Ilman pyproject.toml-dependencies-listaa tiedostoa ei kirjoiteta,
  jotta sama ympäristö voi rakentaa muitakin paketteja.
  '''
  argname = os.path.splitext(basename)[0]
  tiedostolistaus = kokoa_tiedostolistaus(
    projektin_juuri(cmd), cmd.distribution,
  )
  if tiedostolistaus is None:
    cmd.write_or_delete_file(argname, filename, None)
    return
  cmd.write_or_delete_file(
    argname, filename, "\n".join(tiedostolistaus),
  )
  # def kirjoita_asennetut_tiedostot


def projektin_juuri(cmd) -> Path:
  ''' Hakemisto, jossa rakennettavan projektin pyproject.toml on. '''
  juuri = getattr(cmd.distribution, "src_root", None) or os.curdir
  return Path(juuri).resolve()
  # def projektin_juuri


def valimuisti_juuri() -> Path:
  '''
  Levyvälimuistin hakemisto. Sama listaus kelpaa kaikille
  rakennusvaiheille, joilla on sama dependencies-lista.
  '''
  yli = os.environ.get("SETUPTOOLS_TIEDOSTOT_CACHE")
  if yli:
    return Path(yli)
  return Path(tempfile.gettempdir()) / "setuptools-tiedostot"
  # def valimuisti_juuri


def valimuisti_polku(vaatimukset: list[str]) -> Path:
  ''' Vaatimuslistan tiivisteestä muodostettu välimuistitiedosto. '''
  tiiviste = hashlib.sha256(
    "\n".join(vaatimukset).encode("utf-8"),
  ).hexdigest()
  return valimuisti_juuri() / f"{tiiviste}.txt"
  # def valimuisti_polku


def lue_valimuisti(vaatimukset: list[str]) -> list[str] | None:
  ''' Palauta aiemmin koottu listaus tai None. '''
  avain = tuple(vaatimukset)
  if avain in _LISTAUS_VALIMUISTI:
    return _LISTAUS_VALIMUISTI[avain]
  polku = valimuisti_polku(vaatimukset)
  if not polku.is_file():
    return None
  rivit = [
    rivi for rivi in polku.read_text(encoding="utf-8").splitlines()
    if rivi
  ]
  _LISTAUS_VALIMUISTI[avain] = rivit
  return rivit
  # def lue_valimuisti


def kirjoita_valimuisti(
  vaatimukset: list[str],
  rivit: list[str],
) -> None:
  ''' Tallenna listaus prosessin ja levyn välimuistiin. '''
  avain = tuple(vaatimukset)
  _LISTAUS_VALIMUISTI[avain] = rivit
  polku = valimuisti_polku(vaatimukset)
  polku.parent.mkdir(parents=True, exist_ok=True)
  polku.write_text("\n".join(rivit), encoding="utf-8")
  # def kirjoita_valimuisti


def kokoa_tiedostolistaus(juuri: Path, jakelu) -> list[str] | None:
  '''
  Hae pyproject.toml-riippuvuuksien wheelit ja palauta niiden
  tiedostopolut ilman metadatahakemistoja. Sama vaatimuslista
  kootaan vain kerran.
  '''
  vaatimukset = pakettivaatimukset(juuri, jakelu)
  if not vaatimukset:
    return None
  valmis = lue_valimuisti(vaatimukset)
  if valmis is not None:
    return valmis
  with tempfile.TemporaryDirectory(
    prefix="setuptools-tiedostot-",
  ) as tila:
    hakemisto = Path(tila)
    hae_wheelit(vaatimukset, hakemisto)
    rivit = tiedostot_paketeista(hakemisto)
  # with tempfile.TemporaryDirectory
  kirjoita_valimuisti(vaatimukset, rivit)
  return rivit
  # def kokoa_tiedostolistaus


def pakettivaatimukset(juuri: Path, jakelu) -> list[str]:
  '''
  Staattinen tai dynaaminen ``[project] dependencies``.
  Setuptools on ratkaissut listan jakelun install_requires-kenttään.
  Tyhjä, kun dependencies-listaa ei ole määritelty.
  '''
  if not dependencies_maaritetty(juuri):
    return []
  return [
    str(vaatimus)
    for vaatimus in (getattr(jakelu, "install_requires", None) or [])
  ]
  # def pakettivaatimukset


def dependencies_maaritetty(juuri: Path) -> bool:
  '''
  True, jos pyproject.toml määrittelee [project] dependencies
  -listan staattisesti tai dynamic-kentässä.
  '''
  polku = juuri / "pyproject.toml"
  if not polku.is_file():
    return False
  with polku.open("rb") as tiedosto:
    projekti = tomllib.load(tiedosto).get("project") or {}
  # with polku.open
  if "dependencies" in projekti:
    return True
  return "dependencies" in list(projekti.get("dynamic") or [])
  # def dependencies_maaritetty


def hae_wheelit(vaatimukset: list[str], kohde: Path) -> None:
  '''
  Sama haku kuin `pip wheel --wheel-dir kohde <vaatimukset>`,
  pipin konsoliskriptin Python-kutsuna. Vaatimukset ovat
  rakennettavan projektin pyproject.toml-dependencies.
  '''
  from pip._internal.cli.main import main

  koodi = main([
    "wheel",
    "--wheel-dir", str(kohde),
    *vaatimukset,
  ])
  if koodi:
    raise SetupError(f"pip wheel päättyi koodiin {koodi}")
  # def hae_wheelit


def tiedostot_paketeista(hakemisto: Path) -> list[str]:
  ''' Yhdistä hakemiston wheel-pakettien tiedostopolut. '''
  polut: set[str] = set()
  for wheel in sorted(hakemisto.glob("*.whl")):
    polut.update(tiedostot_wheelista(wheel))
  return sorted(polut)
  # def tiedostot_paketeista


def tiedostot_wheelista(wheel: Path) -> list[str]:
  '''
  Listaa wheelin zip-jäsenet. Metadatahakemisto
  `nimi-versio.dist-info` jätetään pois.
  '''
  with zipfile.ZipFile(wheel) as paketti:
    return [
      nimi for nimi in paketti.namelist()
      if not nimi.endswith("/") and not on_metadata(nimi)
    ]
  # with zipfile.ZipFile
  # def tiedostot_wheelista


def on_metadata(polku: str) -> bool:
  ''' Wheelin ensimmäinen polun osa on jakelun dist-info-hakemisto. '''
  osat = PurePosixPath(polku).parts
  return bool(osat) and osat[0].endswith(".dist-info")
  # def on_metadata
