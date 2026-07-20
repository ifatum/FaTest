{ pkgs ? import <nixpkgs> {} }:

pkgs.python3Packages.buildPythonApplication rec {
  pname = "fatest";
  version = "1.1.0";
  format = "pyproject";

  src = ./.;

  nativeBuildInputs = with pkgs.python3Packages; [
    setuptools
  ];

  propagatedBuildInputs = with pkgs.python3Packages; [
    rich
    speedtest-cli
    psutil
  ];

  meta = with pkgs.lib; {
    description = "A fast, clean terminal speedtest tool";
    homepage = "https://github.com/naxce/fatest";
    license = licenses.mit;
    mainProgram = "fatest";
  };
}
