# Submitter: Colin Duquesnoy <colin.duquesnoy@gmail.com>
# Maintainer: Colin Duquesnoy <colin.duquesnoy@gmail.com>
pkgbase=python-qdarkstyle
pkgname=('python2-qdarkstyle' 'python-qdarkstyle')
pkgver=1.16
_pkgver=1.16
pkgrel=1
arch=('any')
url="https://github.com/davidhalter/qdarkstyle"
license=('MIT')
depends=('python2')
makedepends=('python2-setuptools' 'python-setuptools')
source=("https://pypi.python.org/packages/source/Q/QDarkStyle/QDarkStyle-${_pkgver}.tar.gz")
md5sums=('6d742d304406a1a6733a27542402ce82')

build() {
   cd "$srcdir/QDarkStyle-${_pkgver}"
}

package_python-qdarkstyle() {
    pkgdesc="A dark stylesheet for pyside/pyqt applications"
    depends=('python')
    cd "$srcdir/QDarkStyle-${_pkgver}"
    python3 setup.py install --root="$pkgdir/" --optimize=1

    install -D -m644 "$srcdir/QDarkStyle-${_pkgver}/COPYING" $pkgdir/usr/share/licenses/$pkgname/LICENSE
}

package_python2-qdarkstyle() {
    pkgdesc="A dark stylesheet for pyside/pyqt applications"
    depends=('python2')
    cd "$srcdir/QDarkStyle-${_pkgver}"
    python2 setup.py install --root="$pkgdir/" --optimize=1

    install -D -m644 "$srcdir/QDarkStyle-${_pkgver}/COPYING" $pkgdir/usr/share/licenses/$pkgname/LICENSE
}
