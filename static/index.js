(function () {
    "use strict";

    var sticky = false,
        highlighted = [],
        timer = null;

    function $par(el, cls) {
        for (var e = el; e.classList; e = e.parentNode) {
            if (e.classList.contains(cls)) {
                return e;
            }
        }

        return null;
    }

    function highlight(target) {
        var els = document.querySelectorAll('.entry[data-player="' + target.getAttribute("data-player") + '"]');
        for (let i = 0; i < els.length; i++) {
            highlighted.push(els[i]);
            els[i].classList.add("hover");
        }
    }

    function unhighlight() {
        highlighted.forEach(el => el.classList.remove("hover"));
        highlighted = [];
    }

    function refresh(mins) {
        if (mins === 0) {
            return null;
        }

        return window.setTimeout(
            () => window.location.reload(true),
            mins * 60 * 1000);
    }

    document.addEventListener("mouseover", function (e) {
        var target = $par(e.target, "entry");
        if (!sticky && target) {
            highlight(target);
        }
    });

    document.addEventListener("mouseout", function (e) {
        var target = $par(e.target, "entry");
        if (!sticky && target) {
            unhighlight();
        }
    });

    document.addEventListener("click", function (e) {
        var target = $par(e.target, "entry");
        if (target) {
            if (sticky && target.classList.contains("hover")) {
                unhighlight();
                sticky = false;
            } else {
                if (sticky) {
                    unhighlight();
                }

                highlight(target);
                sticky = true;
            }
        }
    });

    document.addEventListener("DOMContentLoaded", function () {
        var interval = sessionStorage.getItem("refreshInterval"),
            e = document.getElementById("refresh-interval");

        if (interval === null) {
            sessionStorage.setItem("refreshInterval", 10);
            interval = 10;
        }

        interval = parseInt(interval, 10);
        timer = refresh(interval);
        for (let i = 0; i < e.options.length; i++) {
            // comparing string to int, so == is necessary
            if (e.options[i].value == interval) {
                e.selectedIndex = i;
                break;
            }
        }

        e.addEventListener("change", function (e) {
            if (timer !== null) {
                window.clearTimeout(timer);
            }

            var interval = parseInt(e.target.options[e.target.selectedIndex].value, 10);
            sessionStorage.setItem("refreshInterval", interval);
            timer = refresh(interval);
        });

    });
})();
