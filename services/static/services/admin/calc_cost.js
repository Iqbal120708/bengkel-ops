(function () {
    "use strict";

    document.addEventListener("DOMContentLoaded", function () {
        const costInput = document.getElementById("id_cost");
        if (!costInput || !costInput.dataset.calcUrl) return;

        function collectRows() {
            const rows = [];
            document
                .querySelectorAll('[name^="items-"][name$="-sparepart"]')
                .forEach(function (el) {
                    const match = el.name.match(/^items-(\d+)-sparepart$/);
                    if (!match) return; // skip baris template __prefix__
                    const prefix = "items-" + match[1] + "-";

                    const del = document.querySelector('[name="' + prefix + 'DELETE"]');
                    if (del && del.checked) return;

                    const qty = document.querySelector('[name="' + prefix + 'quantity_used"]');
                    const price = document.querySelector(
                        '[name="' + prefix + 'price_at_time_of_use"]'
                    );
                    if (!el.value || !qty || !qty.value) return;

                    rows.push([el.value, qty.value, price ? price.value : ""].join(","));
                });
            return rows;
        }

        // Wadah flex: input di kiri (melebar), tombol di kanan
        const wrapper = document.createElement("div");
        wrapper.style.display = "flex";
        wrapper.style.alignItems = "center";
        wrapper.style.gap = "10px";
        wrapper.style.flex = "1";
        wrapper.style.minWidth = "0";

        costInput.parentNode.insertBefore(wrapper, costInput);
        wrapper.append(costInput);
        costInput.style.width = "15em";
        costInput.style.flex = "0 0 auto";

        const link = document.createElement("a");
        link.href = "#";
        link.textContent = "Hitung";
        link.style.whiteSpace = "nowrap";
        wrapper.append(link);

        link.addEventListener("click", function (event) {
            event.preventDefault();

            const params = new URLSearchParams();
            collectRows().forEach(function (row) {
                params.append("row", row);
            });

            const labor = document.getElementById("id_labor_fee");
            params.append("labor", labor ? labor.value : "");

            link.textContent = "...";
            fetch(costInput.dataset.calcUrl + "?" + params.toString(), {
                headers: { "X-Requested-With": "XMLHttpRequest" },
            })
                .then(function (response) {
                    if (!response.ok) throw new Error(response.status);
                    return response.json();
                })
                .then(function (data) {
                    costInput.value = data.cost;
                })
                .catch(function () {
                    alert("Gagal menghitung cost.");
                })
                .finally(function () {
                    link.textContent = "Hitung";
                });
        });
    });
})();