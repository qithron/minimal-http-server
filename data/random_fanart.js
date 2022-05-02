// me not JS dev :)

let NAV = null;
let IMG = null;
let IX = null;
let IY = null;
var ZS = false;

function ONCLICK(e) {
    ZS = !ZS;
    if (ZS) {
        NAV.style.display = 'none';
        IMG.style.width = IX + 'px';
        IMG.style.height = IY + 'px';
        window.scrollTo(e.offsetX, e.offsetY);
    }
    else {
        RESIZE();
    }
}

function RESIZE() {
    if(ZS){return;}
    NAV.style.display = 'block';
    var wx = window.innerWidth;
    var wy = window.innerHeight - NAV.offsetHeight;
    var sx = wy/IY * IX;
    var sy = wx/IX * IY;
    if (sx > wx) {
        IMG.style.width = wx + 'px';
        IMG.style.height = 'unset';
        IMG.style.marginTop = ((wy - sy)/2) + 'px';
    }
    else {
        IMG.style.width = 'unset';
        IMG.style.height = wy + 'px';
        IMG.style.marginTop = 'auto';
    }
}

function FIRST_LOAD() {
    NAV = document.body.childNodes[1];
    IMG = document.body.childNodes[2];
    IX = IMG.width;
    IY = IMG.height;
    document.body.onresize = RESIZE;
    IMG.onclick = ONCLICK;
    RESIZE();
}