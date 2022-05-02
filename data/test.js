async function SEND_REQ(id, method, url) {
    var req = new XMLHttpRequest();
    req.onreadystatechange = function() {
        const e = document.getElementById(id);
        var s = '';
        if (req.readyState == 4) {
            if      (req.status < 200) {s = '_1xx';}
            else if (req.status < 300) {s = '_2xx';}
            else if (req.status < 400) {s = '_3xx';}
            else if (req.status < 500) {s = '_4xx';}
            else if (req.status < 600) {s = '_5xx';}

            e.innerHTML = '<details><summary>' +
                `<span class="${s}">${req.status}</span> ` +
                `<b>${req.statusText}</b> <a href="${url}">${id}</a>` +
                '</summary><p>' +
                    req.getAllResponseHeaders().replaceAll('\r\n', '<br>') +
                '</p></details>';
        }
    };
    req.open(method, url, true);
    req.send();
}