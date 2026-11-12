# -*- coding: utf-8 -*-
'''
Rakenna pieni wheel ja tarkista, että kirjoitin vie
tiedostolistan dist-info-metadataan.
'''

import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
import zipfile
from pathlib import Path


JUURI = Path(__file__).resolve().parents[1]


class TestaaBuild(unittest.TestCase):

  def testaa_lista_paatyy_dist_infoon(self) -> None:
    with tempfile.TemporaryDirectory(prefix="tiedostot-build-") as tila:
      kanta = Path(tila)
      ymp = self._ymparisto(kanta)
      wheel = self._esimerkki_wheel(kanta, ymp)
      for dynaaminen in (False, True):
        with self.subTest(dynaaminen=dynaaminen):
          projekti = self._projekti(
            kanta, wheel, dynaaminen=dynaaminen,
          )
          self._rakenna(projekti, ymp)
          lista = self._lue_lista(projekti)
          self.assertIn("esimerkki/migrations/0001_alku.py", lista)
          self.assertFalse(any(
            ".dist-info/" in rivi for rivi in lista
          ))
    # with tempfile.TemporaryDirectory
    # def testaa_lista_paatyy_dist_infoon

  def _ymparisto(self, kanta: Path) -> Path:
    ymp = kanta / "venv"
    subprocess.check_call(
      [sys.executable, "-m", "venv", str(ymp)],
    )
    pip = ymp / "bin" / "pip"
    subprocess.check_call([
      str(pip), "install", "-e", str(JUURI), "setuptools",
    ])
    subprocess.check_call([str(pip), "install", "build"])
    return ymp
    # def _ymparisto

  def _esimerkki_wheel(self, kanta: Path, ymp: Path) -> Path:
    projekti = kanta / "esimerkki-lahde"
    paketti = projekti / "esimerkki" / "migrations"
    paketti.mkdir(parents=True)
    (projekti / "esimerkki" / "__init__.py").write_text("")
    (paketti / "__init__.py").write_text("")
    (paketti / "0001_alku.py").write_text("# vaellus\n")
    (projekti / "pyproject.toml").write_text(textwrap.dedent('''\
      [build-system]
      requires = ["setuptools"]
      build-backend = "setuptools.build_meta"

      [project]
      name = "esimerkki-paketti"
      version = "0.0.1"

      [tool.setuptools.packages.find]
      where = ["."]
    '''))
    kohde = kanta / "esimerkki-wheel"
    subprocess.check_call([
      str(ymp / "bin" / "pip"), "wheel",
      "--no-deps", "--no-build-isolation",
      "-w", str(kohde), str(projekti),
    ])
    return next(kohde.glob("*.whl"))
    # def _esimerkki_wheel

  def _projekti(
    self, kanta: Path, wheel: Path, *, dynaaminen: bool,
  ) -> Path:
    projekti = kanta / ("dynaaminen" if dynaaminen else "staattinen")
    projekti.mkdir()
    viite = f"esimerkki-paketti @ {wheel.as_uri()}"
    if dynaaminen:
      (projekti / "vaatimukset.txt").write_text(f"{viite}\n")
      (projekti / "pyproject.toml").write_text(textwrap.dedent('''\
        [build-system]
        requires = ["setuptools"]
        build-backend = "setuptools.build_meta"

        [project]
        name = "koe-kokoonpano"
        version = "0.0.1"
        dynamic = ["dependencies"]

        [tool.setuptools.dynamic]
        dependencies = { file = "vaatimukset.txt" }
      '''))
    else:
      (projekti / "pyproject.toml").write_text(textwrap.dedent(f'''\
        [build-system]
        requires = ["setuptools"]
        build-backend = "setuptools.build_meta"

        [project]
        name = "koe-kokoonpano"
        version = "0.0.1"
        dependencies = ["{viite}"]
      '''))
    return projekti
    # def _projekti

  def _rakenna(self, projekti: Path, ymp: Path) -> None:
    ymp_env = os.environ.copy()
    ymp_env["VIRTUAL_ENV"] = str(ymp)
    ymp_env["PATH"] = str(ymp / "bin") + os.pathsep + ymp_env.get(
      "PATH", "",
    )
    subprocess.check_call(
      [str(ymp / "bin" / "python"), "-m", "build", "--no-isolation"],
      cwd=projekti,
      env=ymp_env,
    )
    # def _rakenna

  def _lue_lista(self, projekti: Path) -> list[str]:
    wheel = next((projekti / "dist").glob("*.whl"))
    with zipfile.ZipFile(wheel) as paketti:
      nimi = next(
        polku for polku in paketti.namelist()
        if polku.endswith("asennetut-tiedostot.txt")
      )
      teksti = paketti.read(nimi).decode("utf-8")
    # with zipfile.ZipFile
    return [rivi for rivi in teksti.splitlines() if rivi]
    # def _lue_lista

  # class TestaaBuild


if __name__ == "__main__":
  unittest.main()
