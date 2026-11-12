# -*- coding: utf-8 -*-

import os
import tempfile
import textwrap
import unittest
import zipfile
from pathlib import Path

from setuptools.errors import SetupError

from setuptools_tiedostot import (
  hae_wheelit,
  kirjoita_asennetut_tiedostot,
  kokoa_tiedostolistaus,
  on_metadata,
  pakettivaatimukset,
  projektin_juuri,
  tiedostot_paketeista,
)


class TestaaWheelienTiedostot(unittest.TestCase):

  def testaa_metadata_tunnistetaan(self) -> None:
    self.assertTrue(on_metadata(
      "esimerkki-0.0.1.dist-info/METADATA",
    ))
    self.assertFalse(on_metadata(
      "esimerkki/migrations/0001_alku.py",
    ))
    # def testaa_metadata_tunnistetaan

  def testaa_wheelin_polut_ilman_metadataa(self) -> None:
    with tempfile.TemporaryDirectory() as tila:
      hakemisto = Path(tila)
      wheel = hakemisto / "esimerkki-0.0.1-py3-none-any.whl"
      with zipfile.ZipFile(wheel, "w") as paketti:
        paketti.writestr(
          "esimerkki/migrations/0001_alku.py",
          "# vaellus\n",
        )
        paketti.writestr(
          "esimerkki-0.0.1.dist-info/METADATA",
          "Name: esimerkki\n",
        )
        paketti.writestr(
          "esimerkki/migrations/",
          "",
        )
      polut = tiedostot_paketeista(hakemisto)
    # with tempfile.TemporaryDirectory
    self.assertEqual(
      polut,
      ["esimerkki/migrations/0001_alku.py"],
    )
    # def testaa_wheelin_polut_ilman_metadataa

  # class TestaaWheelienTiedostot


def _esimerkkiwheel(hakemisto: Path) -> Path:
  ''' Paikallinen wheel, jonka pip voi hakea ilman verkkoa. '''
  wheel = hakemisto / "esimerkki-0.0.1-py3-none-any.whl"
  with zipfile.ZipFile(wheel, "w") as paketti:
    paketti.writestr(
      "esimerkki/migrations/0001_alku.py",
      "# vaellus\n",
    )
    paketti.writestr(
      "esimerkki-0.0.1.dist-info/METADATA",
      "Metadata-Version: 2.1\nName: esimerkki\nVersion: 0.0.1\n",
    )
    paketti.writestr(
      "esimerkki-0.0.1.dist-info/WHEEL",
      "Wheel-Version: 1.0\nGenerator: testi\n"
      "Root-Is-Purelib: true\nTag: py3-none-any\n",
    )
  # with zipfile.ZipFile
  return wheel
  # def _esimerkkiwheel


def _jakelu(vaatimukset: list[str] | None = None):
  ''' Jakelu, jonka install_requires on jo ratkaistu. '''
  jakelu = type("Jakelu", (), {})()
  jakelu.install_requires = list(vaatimukset or [])
  return jakelu
  # def _jakelu


def _kirjoita_pyproject(
  juuri: Path,
  dependencies: list[str] | None = None,
  *,
  dynaaminen: bool = False,
) -> None:
  ''' Kirjoita [project], jossa dependencies on staattinen tai dynaaminen. '''
  if dynaaminen:
    teksti = textwrap.dedent('''\
      [project]
      name = "koe"
      version = "0.0.1"
      dynamic = ["dependencies"]
    ''')
  elif dependencies is None:
    teksti = textwrap.dedent('''\
      [project]
      name = "koe"
      version = "0.0.1"
    ''')
  else:
    arvot = ", ".join(repr(vaatimus) for vaatimus in dependencies)
    teksti = textwrap.dedent(f'''\
      [project]
      name = "koe"
      version = "0.0.1"
      dependencies = [{arvot}]
    ''')
  (juuri / "pyproject.toml").write_text(teksti)
  # def _kirjoita_pyproject


class _Komento:
  ''' setuptools-komennon korvike kirjoittimen kutsua varten. '''

  def __init__(
    self,
    juuri: Path | None,
    vaatimukset: list[str] | None = None,
  ) -> None:
    self.distribution = _jakelu(vaatimukset)
    if juuri is not None:
      self.distribution.src_root = str(juuri)
    self.tulos = None
    # def __init__

  def write_or_delete_file(self, argname, filename, data) -> None:
    self.tulos = (argname, filename, data)
    # def write_or_delete_file

  # class _Komento


class TestaaKokoaminen(unittest.TestCase):

  def testaa_projektin_juuri_src_rootista(self) -> None:
    with tempfile.TemporaryDirectory() as tila:
      cmd = _Komento(Path(tila))
      self.assertEqual(
        projektin_juuri(cmd),
        Path(tila).resolve(),
      )
    # with tempfile.TemporaryDirectory
    # def testaa_projektin_juuri_src_rootista

  def testaa_projektin_juuri_tyohakemistosta(self) -> None:
    cmd = _Komento(None)
    self.assertEqual(
      projektin_juuri(cmd),
      Path(os.curdir).resolve(),
    )
    # def testaa_projektin_juuri_tyohakemistosta

  def testaa_kokoa_ilman_dependencies_listaa(self) -> None:
    with tempfile.TemporaryDirectory() as tila:
      juuri = Path(tila)
      self.assertIsNone(
        kokoa_tiedostolistaus(juuri, _jakelu(["esimerkki"])),
      )
      _kirjoita_pyproject(juuri)
      self.assertIsNone(
        kokoa_tiedostolistaus(juuri, _jakelu(["esimerkki"])),
      )
    # with tempfile.TemporaryDirectory
    # def testaa_kokoa_ilman_dependencies_listaa

  def testaa_kokoa_ohittaa_requirements_tiedostot(self) -> None:
    with tempfile.TemporaryDirectory() as tila:
      juuri = Path(tila)
      (juuri / "requirements.txt").write_text("esimerkki\n")
      (juuri / "pypi-paketit.txt").write_text("esimerkki\n")
      _kirjoita_pyproject(juuri)
      self.assertIsNone(kokoa_tiedostolistaus(juuri, _jakelu()))
    # with tempfile.TemporaryDirectory
    # def testaa_kokoa_ohittaa_requirements_tiedostot

  def testaa_pakettivaatimukset_staattisesta_listasta(self) -> None:
    with tempfile.TemporaryDirectory() as tila:
      juuri = Path(tila)
      _kirjoita_pyproject(juuri, ["esimerkki>=1"])
      vaatimukset = pakettivaatimukset(
        juuri, _jakelu(["esimerkki>=1"]),
      )
    # with tempfile.TemporaryDirectory
    self.assertEqual(vaatimukset, ["esimerkki>=1"])
    # def testaa_pakettivaatimukset_staattisesta_listasta

  def testaa_pakettivaatimukset_dynaamisesta_listasta(self) -> None:
    with tempfile.TemporaryDirectory() as tila:
      juuri = Path(tila)
      _kirjoita_pyproject(juuri, dynaaminen=True)
      vaatimukset = pakettivaatimukset(
        juuri, _jakelu(["esimerkki>=1"]),
      )
    # with tempfile.TemporaryDirectory
    self.assertEqual(vaatimukset, ["esimerkki>=1"])
    # def testaa_pakettivaatimukset_dynaamisesta_listasta

  def testaa_kokoa_palauttaa_wheelien_polut(self) -> None:
    with tempfile.TemporaryDirectory() as tila:
      kanta = Path(tila)
      juuri = kanta / "projekti"
      juuri.mkdir()
      wheel = _esimerkkiwheel(kanta)
      viite = f"esimerkki @ {wheel.as_uri()}"
      _kirjoita_pyproject(juuri, [viite])
      polut = kokoa_tiedostolistaus(juuri, _jakelu([viite]))
    # with tempfile.TemporaryDirectory
    self.assertEqual(
      polut,
      ["esimerkki/migrations/0001_alku.py"],
    )
    # def testaa_kokoa_palauttaa_wheelien_polut

  def testaa_kokoa_dynaamisesta_dependenciesista(self) -> None:
    with tempfile.TemporaryDirectory() as tila:
      kanta = Path(tila)
      juuri = kanta / "projekti"
      juuri.mkdir()
      wheel = _esimerkkiwheel(kanta)
      viite = f"esimerkki @ {wheel.as_uri()}"
      _kirjoita_pyproject(juuri, dynaaminen=True)
      polut = kokoa_tiedostolistaus(juuri, _jakelu([viite]))
    # with tempfile.TemporaryDirectory
    self.assertEqual(
      polut,
      ["esimerkki/migrations/0001_alku.py"],
    )
    # def testaa_kokoa_dynaamisesta_dependenciesista

  def testaa_hae_wheelit_tallentaa_paketin(self) -> None:
    with tempfile.TemporaryDirectory() as tila:
      kanta = Path(tila)
      kohde = kanta / "wheelit"
      kohde.mkdir()
      wheel = _esimerkkiwheel(kanta)
      hae_wheelit([f"esimerkki @ {wheel.as_uri()}"], kohde)
      nimet = sorted(polku.name for polku in kohde.glob("*.whl"))
    # with tempfile.TemporaryDirectory
    self.assertEqual(nimet, [wheel.name])
    # def testaa_hae_wheelit_tallentaa_paketin

  def testaa_hae_wheelit_nostaa_virheen(self) -> None:
    with tempfile.TemporaryDirectory() as tila:
      kanta = Path(tila)
      kohde = kanta / "wheelit"
      kohde.mkdir()
      with self.assertRaises(SetupError) as virhe:
        hae_wheelit([str(kanta / "puuttuu.whl")], kohde)
    # with tempfile.TemporaryDirectory
    self.assertEqual(
      str(virhe.exception),
      "pip wheel päättyi koodiin 1",
    )
    # def testaa_hae_wheelit_nostaa_virheen

  def testaa_kirjoitin_poistaa_tiedoston_ilman_listaa(self) -> None:
    with tempfile.TemporaryDirectory() as tila:
      cmd = _Komento(Path(tila))
      kirjoita_asennetut_tiedostot(
        cmd,
        "asennetut-tiedostot.txt",
        "egg-info/asennetut-tiedostot.txt",
      )
    # with tempfile.TemporaryDirectory
    self.assertEqual(cmd.tulos, (
      "asennetut-tiedostot",
      "egg-info/asennetut-tiedostot.txt",
      None,
    ))
    # def testaa_kirjoitin_poistaa_tiedoston_ilman_listaa

  def testaa_kirjoitin_kirjoittaa_polut(self) -> None:
    with tempfile.TemporaryDirectory() as tila:
      kanta = Path(tila)
      juuri = kanta / "projekti"
      juuri.mkdir()
      wheel = _esimerkkiwheel(kanta)
      viite = f"esimerkki @ {wheel.as_uri()}"
      _kirjoita_pyproject(juuri, [viite])
      cmd = _Komento(juuri, [viite])
      kirjoita_asennetut_tiedostot(
        cmd,
        "asennetut-tiedostot.txt",
        "egg-info/asennetut-tiedostot.txt",
      )
    # with tempfile.TemporaryDirectory
    self.assertEqual(cmd.tulos, (
      "asennetut-tiedostot",
      "egg-info/asennetut-tiedostot.txt",
      "esimerkki/migrations/0001_alku.py",
    ))
    # def testaa_kirjoitin_kirjoittaa_polut

  # class TestaaKokoaminen


if __name__ == "__main__":
  unittest.main()
