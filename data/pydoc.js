// me not JS dev :)

let GROUPS = null;

function RESIZE() {
    for (i=0; i<GROUPS.length; i++) {
        if (! GROUPS[i].childElementCount) {continue;}
        GROUPS[i].style.height =
            Math.ceil(GROUPS[i].childElementCount /
                Math.floor(GROUPS[i].clientWidth /
                    GROUPS[i].children[0].clientWidth)) *
            GROUPS[i].children[0].clientHeight + 'px';
    }
}

function FIRST_LOAD() {
    GROUPS = document.getElementsByClassName('in');
    document.body.onresize = RESIZE;
    RESIZE();
}