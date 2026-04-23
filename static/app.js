/* MathLineage - Mathematical Genealogy Browser */
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

    // ── Hashcash PoW (V7 spec s12: 18-bit for free tier) ──────────

    /**
     * Generate a hashcash stamp with the required number of leading
     * zero bits (V7 spec §12, free tier: 18 bits).
     *
     * Batches 256 candidate stamps per Promise.all so the per-digest
     * Promise/await overhead is amortized across many SHA-256 calls.
     * The naive one-await-per-hash loop spends most of its time in
     * Promise/microtask plumbing — batched, 18-bit mining completes in
     * roughly 1 s on a modern CPU instead of 10+ s.
     *
     * Over-work in the final batch is bounded by the batch size (up to
     * 255 extra hashes), negligible compared to the expected ~262 144
     * iterations for 18 bits.
     *
     * @param {number} bits - Required leading zero bits (default 18).
     * @returns {Promise<string>} The hashcash stamp string.
     */
    async function generateHashcash(bits) {
        bits = bits || 18;
        var date = new Date().toISOString().slice(2, 10).replace(/-/g, "");
        var rand = Math.random().toString(36).substring(2, 10);
        var prefix = "1:" + bits + ":" + date + ":gmnap-api::" + rand + ":";

        var encoder = new TextEncoder();  // hoisted — one allocation total
        var batch = 256;
        var counter = 0;
        while (true) {
            var stamps = new Array(batch);
            var promises = new Array(batch);
            for (var i = 0; i < batch; i++) {
                stamps[i] = prefix + (counter + i).toString(16);
                promises[i] = crypto.subtle.digest("SHA-256", encoder.encode(stamps[i]));
            }
            var hashes = await Promise.all(promises);
            for (var j = 0; j < batch; j++) {
                var arr = new Uint8Array(hashes[j]);
                var zeroBits = 0;
                for (var k = 0; k < arr.length; k++) {
                    if (arr[k] === 0) { zeroBits += 8; }
                    else {
                        var b = arr[k];
                        while ((b & 0x80) === 0) { zeroBits++; b <<= 1; }
                        break;
                    }
                }
                if (zeroBits >= bits) return stamps[j];
            }
            counter += batch;
        }
    }

    /**
     * Fetch wrapper that automatically adds hashcash header.
     */
    async function apiFetch(url, options) {
        options = options || {};
        options.headers = options.headers || {};
        if (!options.headers["X-Hashcash"]) {
            options.headers["X-Hashcash"] = await generateHashcash(18);
        }
        return fetch(url, options);
    }

    // ── Utilities ────────────────────────────────────────────────────

    /**
     * Return a country flag emoji for a region code (e.g. "E4" -> Korean flag).
     * Falls back to a globe if mapping unknown.
     */
    var REGION_NAMES = {
        A1: "Anglo-Sphere", A2: "Western Europe", A3: "Nordic-Baltic",
        A4: "Oceania", A5: "Caribbean",
        B1: "East Slavic", B2: "Central European", B3: "Hellenic",
        C1: "Turkic", C2: "Persian-Tajik", C3: "Arabic Levant",
        C4: "Arabic Gulf", C5: "Arabic Maghreb", C6: "Hebrew-Diaspora",
        C7: "Armenian", C8: "Georgian", C9: "Caucasus-Turkic",
        D1: "South Asia Indic", D2: "Dravidian", D3: "Bengali",
        D4: "Pakistan-Urdu", D5: "Sinhala",
        E1: "Chinese (Simplified)", E2: "Chinese (Traditional)",
        E3: "Japanese", E4: "Korean", E5: "Vietnamese",
        E6: "Mainland SE Asia", E7: "Maritime SE Asia",
        F1: "Francophone Africa", F2: "Anglophone Africa",
        F3: "Horn of Africa", F4: "Lusophone Africa",
        G1: "Latin America", H1: "Historical",
        R0: "Residual", Z0: "Quarantine"
    };

    function countryFlag(regionCode) {
        // Representative flags for each region
        var flags = {
            A1: "\uD83C\uDDEC\uD83C\uDDE7", // GB - Anglo
            A2: "\uD83C\uDDE9\uD83C\uDDEA", // DE - Western Europe
            A3: "\uD83C\uDDF8\uD83C\uDDEA", // SE - Nordic
            A4: "\uD83C\uDDEB\uD83C\uDDEF", // FJ - Oceania Pacific
            A5: "\uD83C\uDDEC\uD83C\uDDF5", // GP - Caribbean French
            B1: "\uD83C\uDDF7\uD83C\uDDFA", // RU - Slavic East
            B2: "\uD83C\uDDF5\uD83C\uDDF1", // PL - Slavic Central
            B3: "\uD83C\uDDEC\uD83C\uDDF7", // GR - Hellenic
            C1: "\uD83C\uDDF9\uD83C\uDDF7", // TR - Turkic
            C2: "\uD83C\uDDEE\uD83C\uDDF7", // IR - Persian
            C3: "\uD83C\uDDEA\uD83C\uDDEC", // EG - Arabic Levant/Nile
            C4: "\uD83C\uDDE6\uD83C\uDDEA", // AE - Arabic Gulf
            C5: "\uD83C\uDDE9\uD83C\uDDFF", // DZ - Arabic Maghreb
            C6: "\uD83C\uDDEE\uD83C\uDDF1", // IL - Hebrew
            C7: "\uD83C\uDDE6\uD83C\uDDF2", // AM - Armenian
            C8: "\uD83C\uDDEC\uD83C\uDDEA", // GE - Georgian
            C9: "\uD83C\uDDF1\uD83C\uDDF9", // LT - Baltic
            D1: "\uD83C\uDDEE\uD83C\uDDF3", // IN - South Asian Hindi
            D2: "\uD83C\uDDEE\uD83C\uDDF3", // IN - South Asian Dravidian
            D3: "\uD83C\uDDE7\uD83C\uDDE9", // BD - Bengali
            D4: "\uD83C\uDDF5\uD83C\uDDF0", // PK - Pakistani
            D5: "\uD83C\uDDF1\uD83C\uDDF0", // LK - Sri Lankan
            E1: "\uD83C\uDDE8\uD83C\uDDF3", // CN - Chinese
            E2: "\uD83C\uDDF9\uD83C\uDDFC", // TW - Chinese (Traditional)
            E3: "\uD83C\uDDEF\uD83C\uDDF5", // JP - Japanese
            E4: "\uD83C\uDDF0\uD83C\uDDF7", // KR - Korean
            E5: "\uD83C\uDDFB\uD83C\uDDF3", // VN - Vietnamese
            E6: "\uD83C\uDDF9\uD83C\uDDED", // TH - Thai/SEA
            E7: "\uD83C\uDDEE\uD83C\uDDE9", // ID - Indonesian/SEA
            F1: "\uD83C\uDDF8\uD83C\uDDF3", // SN - SSA Francophone
            F2: "\uD83C\uDDF3\uD83C\uDDEC", // NG - SSA Anglophone
            F3: "\uD83C\uDDEA\uD83C\uDDF9", // ET - Horn of Africa
            F4: "\uD83C\uDDFF\uD83C\uDDE6", // ZA - Southern Africa
            G1: "\uD83C\uDDE7\uD83C\uDDF7"  // BR - Latin American
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
    var apiStatus = document.getElementById("api-status");

    // Views
    var landing = document.getElementById("landing");
    var resultsView = document.getElementById("results-view");
    var profileView = document.getElementById("profile-view");

    // Results
    var resultsTitle = document.getElementById("results-title");
    var resultsList = document.getElementById("results-list");
    var loadingEl = document.getElementById("loading");
    var noResults = document.getElementById("no-results");
    var errorMsg = document.getElementById("error-msg");
    var backToLanding = document.getElementById("back-to-landing");

    // Profile
    var profileContent = document.getElementById("profile-content");
    var backToResults = document.getElementById("back-to-results");

    // Correction dialog
    var corrDialog = document.getElementById("correction-dialog");
    var corrForm = document.getElementById("correction-form");
    var corrOriginalName = document.getElementById("corr-original-name");
    var corrCancel = document.getElementById("corr-cancel");

    // ── View management ──────────────────────────────────────────────

    function showView(viewName) {
        landing.hidden = viewName !== "landing";
        resultsView.hidden = viewName !== "results";
        profileView.hidden = viewName !== "profile";
    }

    backToLanding.addEventListener("click", function () {
        showView("landing");
        searchInput.value = "";
    });

    backToResults.addEventListener("click", function () {
        showView("results");
    });

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

    // ── Search (uses /api/v1/process for enriched data) ──────────────

    var lastSearchResults = [];

    function performSearch(query) {
        if (!query || !query.trim()) return;

        showView("results");
        loadingEl.hidden = false;
        noResults.hidden = true;
        errorMsg.hidden = true;
        resultsList.innerHTML = "";
        resultsTitle.innerHTML = "Results for &ldquo;" + escapeHtml(query.trim()) + "&rdquo;";

        var payload = {
            entries: [{ CanonicalLatin: query.trim() }],
            mode: "quick"
        };

        apiFetch("/api/v1/process", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        })
            .then(function (resp) {
                if (!resp.ok) {
                    return resp.json().then(function (data) {
                        throw new Error(data.detail || "Request failed");
                    });
                }
                return resp.json();
            })
            .then(function (data) {
                loadingEl.hidden = true;
                var entries = data.entries || [];
                lastSearchResults = entries;
                if (entries.length === 0) {
                    noResults.hidden = false;
                    return;
                }
                for (var i = 0; i < entries.length; i++) {
                    renderResultCard(entries[i]);
                }
            })
            .catch(function (err) {
                loadingEl.hidden = true;
                if (!isApiOnline) {
                    errorMsg.hidden = false;
                } else {
                    noResults.hidden = false;
                }
                console.error("Search error:", err);
            });
    }

    var debouncedSearch = debounce(performSearch, 300);

    searchInput.addEventListener("keydown", function (e) {
        if (e.key === "Enter") {
            e.preventDefault();
            performSearch(searchInput.value);
        }
    });

    // Also trigger on input for live-search feel
    searchInput.addEventListener("input", function () {
        if (searchInput.value.trim().length >= 4) {
            debouncedSearch(searchInput.value);
        }
    });

    // ── Result Card Rendering ────────────────────────────────────────

    function confidenceClass(score) {
        if (score >= 0.8) return "confidence-high";
        if (score >= 0.5) return "confidence-medium";
        return "confidence-low";
    }

    function renderResultCard(entry) {
        var card = document.createElement("div");
        card.className = "result-card";
        card.setAttribute("role", "listitem");
        card.setAttribute("tabindex", "0");

        var name = entry.CanonicalLatin || entry.name || "Unknown";
        var region = entry.DetectedRegion || entry.region_code || "";
        var conf = entry.DetectionConfidence || entry.confidence || 0;
        var method = entry.DetectionMethod || entry.detection_method || "";
        var flag = countryFlag(region);
        var confClass = confidenceClass(conf);

        card.innerHTML =
            '<div class="result-name">' + escapeHtml(name) + "</div>" +
            '<div class="result-meta">' +
            "<span>" + escapeHtml(flag) + " " + escapeHtml(REGION_NAMES[region] || region) + " (" + escapeHtml(region) + ")</span>" +
            '<span class="confidence-badge ' + escapeHtml(confClass) + '">' +
            escapeHtml(((conf) * 100).toFixed(1) + "%") + "</span>" +
            "<span>" + escapeHtml(method) + "</span>" +
            "</div>";

        card.addEventListener("click", function () {
            renderProfile(entry);
        });
        card.addEventListener("keydown", function (e) {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                renderProfile(entry);
            }
        });

        resultsList.appendChild(card);
    }

    // ── Profile Rendering ────────────────────────────────────────────

    function renderProfile(entry) {
        showView("profile");

        var name = entry.CanonicalLatin || entry.name || "Unknown";
        var region = entry.DetectedRegion || entry.region_code || "";
        var conf = entry.DetectionConfidence || entry.confidence || 0;
        var flag = countryFlag(region);
        var birthYear = entry.BirthYear || entry.birth_year || "";
        var institution = entry.Institution || entry.institution || "";
        var globalId = entry.GlobalID || entry.global_id || "";

        var html = "";

        // ── Name header ──
        html += '<div class="profile-card">';
        html += '<div class="profile-header">';
        html += '<h2 class="profile-name">' + escapeHtml(name) + "</h2>";
        html += '<div class="profile-region">' + escapeHtml(flag) + " " + escapeHtml(REGION_NAMES[region] || region) + " (" + escapeHtml(region) + ")";
        if (conf > 0) {
            html += ' &middot; ' + escapeHtml(((conf) * 100).toFixed(0) + "% confidence");
        }
        html += "</div>";
        if (birthYear || institution) {
            html += '<div class="profile-bio">';
            if (birthYear) html += "Born: " + escapeHtml(String(birthYear));
            if (birthYear && institution) html += " &middot; ";
            if (institution) html += escapeHtml(institution);
            html += "</div>";
        }
        if (globalId) {
            html += '<div class="profile-id">GlobalID: <code>' + escapeHtml(globalId) + "</code></div>";
        }
        html += "</div>"; // profile-header
        html += "</div>"; // profile-card

        // ── Advisors section ──
        var advisors = entry.Advisors || entry.advisors || entry.advisor_chain || [];
        if (advisors.length > 0) {
            html += '<div class="profile-card">';
            html += '<h3 class="section-title">Doctoral Advisor(s)</h3>';
            for (var i = 0; i < advisors.length; i++) {
                var adv = advisors[i];
                var advName = typeof adv === "string" ? adv : (adv.name || adv.CanonicalLatin || "");
                var advInst = typeof adv === "object" ? (adv.institution || adv.Institution || "") : "";
                var advYear = typeof adv === "object" ? (adv.year || adv.Year || "") : "";

                html += '<div class="advisor-card" tabindex="0" data-advisor-name="' + escapeHtml(advName) + '">';
                html += '<span class="advisor-arrow">&rarr;</span> ';
                html += '<span class="advisor-name">' + escapeHtml(advName) + "</span>";
                if (advInst || advYear) {
                    html += '<div class="advisor-detail">';
                    if (advInst) html += escapeHtml(advInst);
                    if (advInst && advYear) html += ", ";
                    if (advYear) html += "~" + escapeHtml(String(advYear));
                    html += "</div>";
                }
                html += "</div>";
            }
            html += "</div>"; // profile-card
        }

        // ── Genealogy tree (rendered async after DOM insertion) ──
        if (advisors.length > 0) {
            html += '<div class="profile-card genealogy-tree-panel" id="genealogy-tree-panel">';
            html += '<div class="tree-header">';
            html += '<h3 class="section-title">Advisor Tree</h3>';
            html += '<label class="tree-depth-label">Depth ';
            html += '<select id="tree-depth" aria-label="Tree depth">';
            html += '<option value="3">3</option>';
            html += '<option value="5" selected>5</option>';
            html += '<option value="8">8</option>';
            html += "</select></label>";
            html += "</div>";
            html += '<div class="tree-status" id="tree-status">Loading tree&hellip;</div>';
            html += '<svg id="genealogy-tree-svg" class="genealogy-tree-svg" aria-label="Doctoral advisor tree" role="img"></svg>';
            html += '<div class="tree-hint">Scroll to zoom, drag to pan. Click a node to open it.</div>';
            html += "</div>";
        }

        // ── Authority Sources ──
        var sources = entry.Sources || entry.AuthoritySources || entry.authority_sources || [];
        if (sources.length > 0) {
            html += '<div class="profile-card">';
            html += '<h3 class="section-title">Authority Sources</h3>';
            html += '<div class="source-badges">';
            for (var s = 0; s < sources.length; s++) {
                var srcName = typeof sources[s] === "string" ? sources[s] : (sources[s].name || sources[s].source || "");
                html += '<span class="source-badge">' + escapeHtml(srcName) + "</span>";
            }
            html += "</div></div>";
        }

        // ── Name Variants / Short Forms ──
        var variants = entry.ShortForms || entry.NameVariants || entry.name_variants || entry.short_forms || entry.Variants || [];
        // If Variants is a dict with Observed/Synthesised, flatten it
        if (variants && typeof variants === "object" && !Array.isArray(variants)) {
            var flat = [];
            if (variants.Observed) flat = flat.concat(variants.Observed);
            if (variants.Synthesised) flat = flat.concat(variants.Synthesised);
            variants = flat;
        }
        if (variants.length > 0) {
            html += '<div class="profile-card">';
            html += '<h3 class="section-title">Name Variants</h3>';
            html += '<div class="variant-tags">';
            for (var v = 0; v < variants.length; v++) {
                var varName = typeof variants[v] === "string" ? variants[v] : (variants[v].form || "");
                html += '<span class="variant-tag">' + escapeHtml(varName) + "</span>";
            }
            html += "</div></div>";
        }

        // ── Ancestor chain (if available) ──
        var ancestors = entry.AncestorChain || entry.ancestor_chain || [];
        if (ancestors.length > 0) {
            html += '<div class="profile-card">';
            html += '<h3 class="section-title">Ancestor Chain</h3>';
            html += '<div class="ancestor-chain">';
            for (var a = 0; a < ancestors.length; a++) {
                var ancName = typeof ancestors[a] === "string" ? ancestors[a] : (ancestors[a].name || "");
                html += '<div class="ancestor-node">';
                html += '<span class="ancestor-name">' + escapeHtml(ancName) + "</span>";
                html += "</div>";
                if (a < ancestors.length - 1) {
                    html += '<div class="ancestor-connector"></div>';
                }
            }
            html += "</div></div>";
        }

        // ── Metadata (raw, collapsed) ──
        var metadata = entry.metadata || entry.Metadata || null;
        if (metadata && typeof metadata === "object") {
            var filtered = {};
            var INTERNAL = ["_processor", "_region_processed", "GraphCoherence", "BayesianCoherence", "AuthorityConfidence", "BetweennessScore"];
            for (var key in metadata) {
                if (INTERNAL.indexOf(key) === -1) {
                    filtered[key] = metadata[key];
                }
            }
            if (Object.keys(filtered).length > 0) {
                html += '<div class="profile-card">';
                html += '<h3 class="section-title">Detection Metadata</h3>';
                html += '<pre class="metadata-raw">' + escapeHtml(JSON.stringify(filtered, null, 2)) + "</pre>";
                html += "</div>";
            }
        }

        // ── Suggest Correction button ──
        html += '<div class="profile-actions">';
        html += '<button class="btn-correction" id="open-correction">Suggest Correction</button>';
        html += "</div>";

        profileContent.innerHTML = html;

        // ── Bind advisor clicks ──
        var advisorCards = profileContent.querySelectorAll(".advisor-card");
        for (var ac = 0; ac < advisorCards.length; ac++) {
            advisorCards[ac].addEventListener("click", function () {
                var advName = this.getAttribute("data-advisor-name");
                if (advName) {
                    searchInput.value = advName;
                    performSearch(advName);
                }
            });
            advisorCards[ac].addEventListener("keydown", function (e) {
                if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    var advName = this.getAttribute("data-advisor-name");
                    if (advName) {
                        searchInput.value = advName;
                        performSearch(advName);
                    }
                }
            });
        }

        // ── Bind correction button ──
        var corrBtn = document.getElementById("open-correction");
        if (corrBtn) {
            corrBtn.addEventListener("click", function () {
                corrOriginalName.value = name;
                corrDialog.showModal();
            });
        }

        // ── Render genealogy tree (async; after DOM insertion) ──
        if (advisors.length > 0) {
            var depthSel = document.getElementById("tree-depth");
            if (depthSel) {
                depthSel.addEventListener("change", function () {
                    renderGenealogyTree(entry, parseInt(depthSel.value, 10) || 5);
                });
            }
            renderGenealogyTree(entry, 5);
        }
    }

    // ── Genealogy tree rendering (d3 v7) ───────────────────────────

    /**
     * Build a hierarchy from the flat edge list returned by
     * /api/v1/lineage. Each edge is {from, to, relation}. The root
     * is the person the caller queried. We duplicate shared ancestors
     * at each occurrence (d3.hierarchy requires a strict tree).
     */
    function edgesToHierarchy(rootId, edges) {
        // Build adjacency: from -> [to, to, ...]
        var childrenOf = {};
        for (var i = 0; i < edges.length; i++) {
            var e = edges[i];
            if (!e || !e.from || !e.to) continue;
            (childrenOf[e.from] = childrenOf[e.from] || []).push(e.to);
        }
        // Recursively build tree, duplicating shared nodes (DAG → tree).
        // Guard against cycles with a per-path visited set.
        function build(id, pathSet) {
            var node = { id: id, name: id, children: [] };
            if (pathSet[id]) {
                // Cycle — stop expansion at this node but keep the label.
                node.isCycle = true;
                return node;
            }
            var nextPath = Object.assign({}, pathSet);
            nextPath[id] = true;
            var kids = childrenOf[id] || [];
            for (var j = 0; j < kids.length; j++) {
                node.children.push(build(kids[j], nextPath));
            }
            return node;
        }
        return build(rootId, {});
    }

    /**
     * Fetch the lineage for this entry and render an SVG tree.
     * Silently no-ops if d3 is missing (e.g. offline asset blocked).
     */
    function renderGenealogyTree(entry, depth) {
        var svg = document.getElementById("genealogy-tree-svg");
        var statusEl = document.getElementById("tree-status");
        if (!svg || !statusEl) return;
        if (typeof d3 === "undefined") {
            statusEl.textContent = "Tree library failed to load.";
            statusEl.className = "tree-status tree-error";
            svg.hidden = true;
            return;
        }

        statusEl.textContent = "Loading tree\u2026";
        statusEl.className = "tree-status";
        // Clear any previous render
        while (svg.firstChild) svg.removeChild(svg.firstChild);

        var canonical = entry.CanonicalLatin || entry.name || "";
        // Prefer name-based lookup: pipeline GlobalIDs don't match the curated
        // genealogy enrichment keys (Wikidata-sourced), but CanonicalLatin does.
        // Fall through to GlobalID only if we have no name.
        var rootId = canonical ? ("name:" + canonical)
            : (entry.GlobalID || entry.global_id || "");
        if (!rootId) {
            statusEl.textContent = "No identifier for lineage lookup.";
            statusEl.className = "tree-status tree-empty";
            svg.hidden = true;
            return;
        }
        var url = "/api/v1/lineage/" + encodeURIComponent(rootId) + "?depth=" + encodeURIComponent(depth);

        apiFetch(url)
            .then(function (resp) {
                if (resp.status === 404) {
                    statusEl.textContent = "No advisor chain available for this record.";
                    statusEl.className = "tree-status tree-empty";
                    svg.hidden = true;
                    return null;
                }
                if (!resp.ok) {
                    throw new Error("Lineage fetch failed: " + resp.status);
                }
                return resp.json();
            })
            .then(function (data) {
                if (!data) return;
                var edges = (data && data.edges) || [];
                if (edges.length === 0) {
                    statusEl.textContent = "No advisor chain available for this record.";
                    statusEl.className = "tree-status tree-empty";
                    svg.hidden = true;
                    return;
                }
                svg.hidden = false;
                statusEl.textContent = "";
                // Server returns edges with the display name as endpoints
                // (not "name:..." form). Use the first edge's from, or
                // the stripped root, to match.
                var treeRoot = (data.root || rootId).replace(/^name:/, "");
                if (edges[0] && edges[0].from) treeRoot = edges[0].from;
                drawTree(svg, treeRoot, edges);
            })
            .catch(function (err) {
                console.error("Tree render error:", err);
                statusEl.textContent = "Failed to load advisor tree.";
                statusEl.className = "tree-status tree-error";
                svg.hidden = true;
            });
    }

    /**
     * Lay out a d3.hierarchy and render nodes/links into the SVG.
     * Orientation: root at top, ancestors downward.
     */
    function drawTree(svgEl, rootId, edges) {
        var hierData = edgesToHierarchy(rootId, edges);
        var root = d3.hierarchy(hierData);

        // Measure container — the SVG inherits CSS width, but we need numeric
        // dimensions for d3.tree().size().
        var width = svgEl.clientWidth || 760;
        var descendants = root.descendants();
        var leafCount = Math.max(1, root.leaves().length);
        var depth = root.height || 1;
        var nodeVSpacing = 70;   // vertical px per depth level
        var height = Math.max(240, (depth + 1) * nodeVSpacing + 40);

        // Compute a comfortable width: at least the container, but wider if
        // we have many leaves so labels don't collide.
        var minPxPerLeaf = 160;
        var contentWidth = Math.max(width - 40, leafCount * minPxPerLeaf);

        var treeLayout = d3.tree().size([contentWidth, height - 60]);
        treeLayout(root);

        // d3.tree places the root at y=0; we want root at top with children
        // below, which is already the default when using .size([w, h]).

        // Set up svg
        var svg = d3.select(svgEl);
        svg.attr("viewBox", "0 0 " + width + " " + height)
            .attr("preserveAspectRatio", "xMidYMin meet")
            .attr("height", height);

        // A group that we'll transform with zoom/pan.
        var g = svg.append("g").attr("class", "tree-viewport");

        // Center the tree horizontally inside the svg viewport if smaller
        var xOffset = 20;
        if (contentWidth < width - 40) {
            xOffset = (width - contentWidth) / 2;
        }
        g.attr("transform", "translate(" + xOffset + "," + 30 + ")");

        // Links
        var linkGen = d3.linkVertical().x(function (d) { return d.x; }).y(function (d) { return d.y; });
        g.append("g")
            .attr("class", "tree-links")
            .selectAll("path")
            .data(root.links())
            .join("path")
            .attr("class", "tree-link")
            .attr("d", linkGen);

        // Nodes
        var nodeG = g.append("g")
            .attr("class", "tree-nodes")
            .selectAll("g")
            .data(descendants)
            .join("g")
            .attr("class", function (d) {
                var cls = "tree-node";
                if (d.depth === 0) cls += " tree-node-root";
                if (d.data.isCycle) cls += " tree-node-cycle";
                return cls;
            })
            .attr("transform", function (d) { return "translate(" + d.x + "," + d.y + ")"; })
            .attr("tabindex", "0")
            .attr("role", "button")
            .attr("aria-label", function (d) { return d.data.name; });

        nodeG.append("circle").attr("r", 6);

        nodeG.append("text")
            .attr("dy", "1.6em")
            .attr("text-anchor", "middle")
            .text(function (d) {
                var label = labelFromId(d.data.name);
                if (label.length > 28) label = label.slice(0, 26) + "\u2026";
                return label;
            });

        // Full-name tooltip
        nodeG.append("title").text(function (d) { return d.data.name; });

        // Click → search that node
        nodeG.on("click", function (_event, d) {
            if (d.depth === 0) return; // root is already open
            var label = labelFromId(d.data.name);
            if (!label) return;
            searchInput.value = label;
            performSearch(label);
        });
        nodeG.on("keydown", function (event, d) {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                if (d.depth === 0) return;
                var label = labelFromId(d.data.name);
                if (!label) return;
                searchInput.value = label;
                performSearch(label);
            }
        });

        // Zoom/pan
        var zoom = d3.zoom()
            .scaleExtent([0.4, 3])
            .on("zoom", function (event) {
                g.attr("transform", event.transform);
            });
        svg.call(zoom);
        // Initialize transform so wheel zoom is smooth from current position
        svg.call(zoom.transform, d3.zoomIdentity.translate(xOffset, 30));
    }

    /**
     * Turn an advisor node id into a human-readable label.
     * GlobalIDs are opaque; `name:Euler, Leonhard` → `Euler, Leonhard`;
     * plain strings pass through.
     */
    function labelFromId(id) {
        if (!id) return "";
        if (id.indexOf("name:") === 0) return id.slice(5);
        return id;
    }

    // ── Correction Dialog ────────────────────────────────────────────

    corrCancel.addEventListener("click", function () {
        corrDialog.close();
    });

    corrForm.addEventListener("submit", function (e) {
        e.preventDefault();

        var submitBtn = corrForm.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        submitBtn.textContent = "Submitting...";

        var payload = {
            original_name: corrOriginalName.value,
            correction_type: document.getElementById("corr-type").value,
            suggested_value: document.getElementById("corr-value").value,
            source_url: document.getElementById("corr-source").value,
            submitter_note: document.getElementById("corr-note").value
        };

        apiFetch("/api/v1/suggest", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        })
            .then(function (resp) {
                if (!resp.ok) throw new Error("Submission failed");
                return resp.json();
            })
            .then(function () {
                corrDialog.close();
                corrForm.reset();
                submitBtn.disabled = false;
                submitBtn.textContent = "Submit Suggestion";
                // Show brief thank-you
                var msg = document.createElement("div");
                msg.className = "toast";
                msg.textContent = "Thank you! Your suggestion has been received.";
                document.body.appendChild(msg);
                setTimeout(function () { msg.remove(); }, 3000);
            })
            .catch(function (err) {
                console.error("Correction submission error:", err);
                submitBtn.disabled = false;
                submitBtn.textContent = "Submit Suggestion";
            });
    });

    // ── Keyboard Shortcuts ───────────────────────────────────────────

    document.addEventListener("keydown", function (e) {
        // "/" to focus search (only when not already in an input)
        if (e.key === "/" && document.activeElement !== searchInput &&
            document.activeElement.tagName !== "INPUT" &&
            document.activeElement.tagName !== "TEXTAREA" &&
            document.activeElement.tagName !== "SELECT") {
            e.preventDefault();
            searchInput.focus();
        }

        // Escape to go back
        if (e.key === "Escape") {
            if (!corrDialog.open && !profileView.hidden) {
                showView("results");
            } else if (!corrDialog.open && !resultsView.hidden) {
                showView("landing");
                searchInput.value = "";
            }
        }
    });

    // Expose for testing
    window.escapeHtml = escapeHtml;
    window.countryFlag = countryFlag;
    window.formatDuration = formatDuration;
})();
