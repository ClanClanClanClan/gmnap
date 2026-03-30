/* GMNAP V7 - Web Interface Application */
"use strict";

(function () {
    // ── XSS Prevention ──────────────────────────────────────────────

    /**
     * Escape HTML special characters to prevent XSS.
     * @param {string} str - Raw string to escape.
     * @returns {string} Escaped string safe for innerHTML.
     */
    function escapeHtml(str) {
        if (typeof str !== "string") {
            str = String(str == null ? "" : str);
        }
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;")
            .replace(/`/g, "&#96;");
    }

    // ── Utilities ────────────────────────────────────────────────────

    /**
     * Return a country flag emoji for a region code (e.g. "E4" -> "").
     * Falls back to a globe if mapping unknown.
     */
    function countryFlag(regionCode) {
        var flags = {
            A1: "\uD83C\uDDEC\uD83C\uDDE7", A2: "\uD83C\uDDE9\uD83C\uDDEA",
            A3: "\uD83C\uDDEB\uD83C\uDDF7", A4: "\uD83C\uDDEA\uD83C\uDDF8",
            A5: "\uD83C\uDDF5\uD83C\uDDF9",
            B1: "\uD83C\uDDF7\uD83C\uDDFA", B2: "\uD83C\uDDFA\uD83C\uDDE6",
            B3: "\uD83C\uDDF5\uD83C\uDDF1",
            C1: "\uD83C\uDDF0\uD83C\uDDFF", C2: "\uD83C\uDDF9\uD83C\uDDF7",
            C3: "\uD83C\uDDEE\uD83C\uDDF7", C4: "\uD83C\uDDE6\uD83C\uDDEA",
            C5: "\uD83C\uDDEE\uD83C\uDDF1", C6: "\uD83C\uDDEA\uD83C\uDDF9",
            C7: "\uD83C\uDDEC\uD83C\uDDEA", C8: "\uD83C\uDDE6\uD83C\uDDF2",
            C9: "\uD83C\uDDEC\uD83C\uDDF7",
            D1: "\uD83C\uDDEE\uD83C\uDDF3", D2: "\uD83C\uDDEE\uD83C\uDDF3",
            D3: "\uD83C\uDDE7\uD83C\uDDE9", D4: "\uD83C\uDDF5\uD83C\uDDF0",
            D5: "\uD83C\uDDF1\uD83C\uDDF0",
            E1: "\uD83C\uDDE8\uD83C\uDDF3", E2: "\uD83C\uDDEF\uD83C\uDDF5",
            E3: "\uD83C\uDDF9\uD83C\uDDFC", E4: "\uD83C\uDDF0\uD83C\uDDF7",
            E5: "\uD83C\uDDFB\uD83C\uDDF3", E6: "\uD83C\uDDF9\uD83C\uDDED",
            E7: "\uD83C\uDDEE\uD83C\uDDE9",
            F1: "\uD83C\uDDF3\uD83C\uDDEC", F2: "\uD83C\uDDFF\uD83C\uDDE6",
            F3: "\uD83C\uDDEA\uD83C\uDDF9", F4: "\uD83C\uDDE8\uD83C\uDDE9"
        };
        return flags[regionCode] || "\uD83C\uDF0D";
    }

    /**
     * Format milliseconds as a human-readable duration.
     */
    function formatDuration(ms) {
        if (ms < 1000) return ms + "ms";
        if (ms < 60000) return (ms / 1000).toFixed(1) + "s";
        return (ms / 60000).toFixed(1) + "min";
    }

    /**
     * Debounce a function call.
     */
    function debounce(fn, delay) {
        var timer = null;
        return function () {
            var args = arguments;
            var ctx = this;
            if (timer) clearTimeout(timer);
            timer = setTimeout(function () {
                fn.apply(ctx, args);
            }, delay);
        };
    }

    // ── DOM Elements ─────────────────────────────────────────────────

    var searchInput = document.getElementById("search-input");
    var searchBtn = document.getElementById("search-btn");
    var resultsSection = document.getElementById("results-section");
    var resultsContainer = document.getElementById("results-container");
    var loadingSpinner = document.getElementById("loading-spinner");
    var noResults = document.getElementById("no-results");
    var errorMessage = document.getElementById("error-message");
    var apiStatus = document.getElementById("api-status");
    var detailPanel = document.getElementById("detail-panel");
    var detailBody = document.getElementById("detail-body");
    var detailClose = document.getElementById("detail-close");

    // ── API Health Check ─────────────────────────────────────────────

    var isApiOnline = false;

    function checkApiHealth() {
        fetch("/healthz")
            .then(function (resp) {
                if (resp.ok) {
                    isApiOnline = true;
                    apiStatus.textContent = "API Online";
                    apiStatus.className = "status-indicator status-online";
                } else {
                    throw new Error("not ok");
                }
            })
            .catch(function () {
                isApiOnline = false;
                apiStatus.textContent = "API Offline";
                apiStatus.className = "status-indicator status-offline";
            });
    }

    checkApiHealth();
    setInterval(checkApiHealth, 30000);

    // ── Search ───────────────────────────────────────────────────────

    function performSearch(query) {
        if (!query || !query.trim()) return;

        resultsSection.hidden = false;
        loadingSpinner.hidden = false;
        noResults.hidden = true;
        errorMessage.hidden = true;
        resultsContainer.innerHTML = "";

        fetch("/api/v1/query?name=" + encodeURIComponent(query.trim()))
            .then(function (resp) {
                if (!resp.ok) {
                    return resp.json().then(function (data) {
                        throw new Error(data.detail || "Request failed");
                    });
                }
                return resp.json();
            })
            .then(function (data) {
                loadingSpinner.hidden = true;
                if (!data || (!data.name && !data.region_code)) {
                    noResults.hidden = false;
                    return;
                }
                renderResult(data);
            })
            .catch(function (err) {
                loadingSpinner.hidden = true;
                if (!isApiOnline) {
                    errorMessage.hidden = false;
                } else {
                    noResults.hidden = false;
                }
                console.error("Search error:", err);
            });
    }

    var debouncedSearch = debounce(performSearch, 300);

    searchInput.addEventListener("input", function () {
        debouncedSearch(searchInput.value);
    });

    searchBtn.addEventListener("click", function () {
        performSearch(searchInput.value);
    });

    searchInput.addEventListener("keydown", function (e) {
        if (e.key === "Enter") {
            e.preventDefault();
            performSearch(searchInput.value);
        }
    });

    // ── Result Rendering ─────────────────────────────────────────────

    function confidenceClass(score) {
        if (score >= 0.8) return "confidence-high";
        if (score >= 0.5) return "confidence-medium";
        return "confidence-low";
    }

    function renderResult(data) {
        var card = document.createElement("div");
        card.className = "result-card";
        card.setAttribute("role", "listitem");
        card.setAttribute("tabindex", "0");
        card.setAttribute("aria-label", "Result for " + escapeHtml(data.name));

        var flag = countryFlag(data.region_code);
        var confClass = confidenceClass(data.confidence || 0);

        card.innerHTML =
            '<div class="result-name">' + escapeHtml(data.name) + "</div>" +
            '<div class="result-meta">' +
            "<span>" + escapeHtml(flag) + " " + escapeHtml(data.region_code || "Unknown") + "</span>" +
            '<span class="confidence-badge ' + escapeHtml(confClass) + '">' +
            escapeHtml(((data.confidence || 0) * 100).toFixed(1) + "%") +
            "</span>" +
            "<span>" + escapeHtml(data.detection_method || "") + "</span>" +
            "</div>";

        card.addEventListener("click", function () {
            showDetail(data);
        });
        card.addEventListener("keydown", function (e) {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                showDetail(data);
            }
        });

        resultsContainer.appendChild(card);
    }

    // ── Detail Panel ─────────────────────────────────────────────────

    function showDetail(data) {
        detailPanel.hidden = false;

        var html = "";
        var fields = [
            ["Name", data.name],
            ["Region Code", data.region_code],
            ["Confidence", ((data.confidence || 0) * 100).toFixed(1) + "%"],
            ["Detection Method", data.detection_method],
            ["GlobalID", data.global_id]
        ];

        for (var i = 0; i < fields.length; i++) {
            var label = fields[i][0];
            var value = fields[i][1];
            if (value == null) continue;
            html +=
                '<div class="detail-field">' +
                '<div class="detail-field-label">' + escapeHtml(label) + "</div>" +
                '<div class="detail-field-value">' + escapeHtml(value);

            if (label === "GlobalID") {
                html += '<button class="copy-btn" data-copy="' + escapeHtml(value) +
                    '" aria-label="Copy GlobalID to clipboard">Copy</button>';
            }
            html += "</div></div>";
        }

        if (data.metadata) {
            html += '<div class="detail-field">' +
                '<div class="detail-field-label">Metadata</div>' +
                '<div class="detail-field-value"><pre>' +
                escapeHtml(JSON.stringify(data.metadata, null, 2)) +
                "</pre></div></div>";
        }

        detailBody.innerHTML = html;

        // Bind copy buttons
        var copyBtns = detailBody.querySelectorAll(".copy-btn");
        for (var j = 0; j < copyBtns.length; j++) {
            copyBtns[j].addEventListener("click", function (e) {
                e.stopPropagation();
                var text = this.getAttribute("data-copy");
                if (navigator.clipboard) {
                    navigator.clipboard.writeText(text).catch(function (err) {
                        console.error("Copy failed:", err);
                    });
                }
            });
        }

        searchInput.setAttribute("aria-expanded", "true");
    }

    function closeDetail() {
        detailPanel.hidden = true;
        searchInput.setAttribute("aria-expanded", "false");
    }

    detailClose.addEventListener("click", closeDetail);

    // ── Keyboard Shortcuts ───────────────────────────────────────────

    document.addEventListener("keydown", function (e) {
        // "/" to focus search (only when not already in an input)
        if (e.key === "/" && document.activeElement !== searchInput &&
            document.activeElement.tagName !== "INPUT" &&
            document.activeElement.tagName !== "TEXTAREA") {
            e.preventDefault();
            searchInput.focus();
        }

        // Escape to close detail panel
        if (e.key === "Escape") {
            if (!detailPanel.hidden) {
                closeDetail();
            }
        }
    });

    // Expose escapeHtml for testing
    window.escapeHtml = escapeHtml;
    window.countryFlag = countryFlag;
    window.formatDuration = formatDuration;
})();
