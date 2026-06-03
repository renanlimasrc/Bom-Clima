#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

PKGNAME="bom-clima"
VERSION="$(python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")"
DIST_DIR="$PROJECT_ROOT/dist"
BUILD_DIR="$PROJECT_ROOT/build/arch"

echo "==> Building ${PKGNAME} ${VERSION} for Arch Linux..."

mkdir -p "$DIST_DIR" "$BUILD_DIR"
cd "$BUILD_DIR"

echo "==> Creating source tarball..."
TARBALL="${PKGNAME}-${VERSION}.tar.gz"
tar czf "$TARBALL" \
    --transform "s,^$(basename "$PROJECT_ROOT"),${PKGNAME}-${VERSION}," \
    --exclude='build' \
    --exclude='dist' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='.mypy_cache' \
    --exclude='.pytest_cache' \
    --exclude='.ruff_cache' \
    -C "$(dirname "$PROJECT_ROOT")" "$(basename "$PROJECT_ROOT")"

SHA256="$(sha256sum "$TARBALL" | awk '{print $1}')"

echo "==> Generating PKGBUILD..."
cat > PKGBUILD <<PKGEOF
# Maintainer: ninrod <renanlimasrc>
pkgname=$PKGNAME
pkgver=$VERSION
pkgrel=1
pkgdesc="Beautiful CLI weather app powered by Open-Meteo API"
arch=('any')
url="https://github.com/renanlimasrc/Bom-Clima"
license=('GPL-2.0-or-later')
depends=('python' 'python-requests' 'python-rich')
makedepends=('python-build' 'python-installer' 'python-hatchling')
source=("$TARBALL")
sha256sums=('$SHA256')

build() {
    cd "${PKGNAME}-\${pkgver}"
    python -m build --wheel --no-isolation
}

package() {
    cd "${PKGNAME}-\${pkgver}"
    python -m installer --destdir="\${pkgdir}" dist/*.whl
}
PKGEOF

echo "==> Building package..."
makepkg -s --nocheck --noconfirm

PKG_FILE=$(ls *.pkg.tar.zst)
cp "$PKG_FILE" "$DIST_DIR/"

cd "$PROJECT_ROOT"
rm -rf build

echo ""
echo "==> Package created: dist/$PKG_FILE"
