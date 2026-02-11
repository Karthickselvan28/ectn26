/**
 * TN Elections 2021 - Multi-Constituency Table-Centric UI
 */

// ===========================
// Constants
// ===========================
const MASTER_DATA_PATH = 'data/master.json';
const DISTRICT_SUMMARY_PATH = 'data/district_summary.json';
const GEOHASH_PRECISION = 6;
const ITEMS_PER_PAGE = 50;

const COLORS = {
    dmk: '#dc2626',
    aiadmk: '#16a34a',
    swing: '#f59e0b'
};

// ===========================
// Global State
// ===========================
let map;
let masterData = null;
let districtSummary = null;
let currentView = 'overview'; // 'overview' or 'booth-analysis'
let selectedArea = null;
let currentConstituency = null;
let allBooths = [];
let filteredBooths = [];
let geohashAreas = new Map();
let geohashLayers = [];
let currentPage = 1;
let currentSort = { column: 'booth_no', ascending: true };
let selectedBoothId = null;
let activeFilter = null; // Track active category filter

// ===========================
// Initialization
// ===========================
async function init() {
    try {
        // Load district summary
        const summaryResponse = await fetch(DISTRICT_SUMMARY_PATH);
        if (!summaryResponse.ok) throw new Error('Failed to load district summary');
        districtSummary = await summaryResponse.json();

        // Load master data
        const response = await fetch(MASTER_DATA_PATH);
        if (!response.ok) throw new Error('Failed to load master data');
        masterData = await response.json();

        // Initialize map (but keep hidden initially)
        initMap();

        // Set up event listeners
        setupEventListeners();

        // Handle browser back/forward
        window.addEventListener('popstate', (event) => {
            if (event.state && event.state.view === 'booth-analysis') {
                showBoothAnalysis(event.state.area, true);
            } else {
                showDistrictOverview(true);
            }
        });

        // Show district overview and set initial history state
        history.replaceState({ view: 'overview' }, '', '');
        showDistrictOverview();

        console.log('✅ Application initialized');
    } catch (error) {
        console.error('Error initializing app:', error);
    }
}

// ===========================
// View Management
// ===========================
function showDistrictOverview(fromPopstate = false) {
    currentView = 'overview';

    // Show/hide sections
    document.getElementById('district-overview').style.display = 'block';
    document.getElementById('booth-analysis').style.display = 'none';
    document.getElementById('back-btn').style.display = 'none';
    document.getElementById('area-selector').style.display = 'none';
    document.getElementById('mode-selector').style.display = 'none';

    // Reset subtitle
    document.getElementById('header-subtitle').textContent = 'Kanchipuram District';

    // Push history state (only if not from popstate)
    if (!fromPopstate) {
        history.pushState({ view: 'overview' }, '', '');
    }

    // Render district summary
    renderDistrictSummary();
    renderAreaCards();
}

function showBoothAnalysis(areaName, fromPopstate = false) {
    currentView = 'booth-analysis';
    selectedArea = areaName;

    // Show/hide sections
    document.getElementById('district-overview').style.display = 'none';
    document.getElementById('booth-analysis').style.display = 'block';
    document.getElementById('back-btn').style.display = 'block';
    document.getElementById('area-selector').style.display = 'flex';

    // Update subtitle
    document.getElementById('header-subtitle').textContent = `${areaName} - Booth Analysis`;

    // Push history state (only if not from popstate)
    if (!fromPopstate) {
        history.pushState({ view: 'booth-analysis', area: areaName }, '', '');
    }

    // Load the area's data
    const area = districtSummary.areas.find(a => a.name === areaName);
    if (area) {
        loadConstituency(area.data_file).then(() => {
            // Refresh map after view switch - multiple calls to ensure tiles load
            setTimeout(() => {
                if (map) {
                    map.invalidateSize();
                    renderGeohashAreas(); // Re-render markers after map is resized
                }
            }, 200);
            setTimeout(() => {
                if (map) {
                    map.invalidateSize();
                }
            }, 500);
        });
    }
}

function renderDistrictSummary() {
    const totals = districtSummary.totals;

    // Update stats
    document.getElementById('district-total-booths').textContent = totals.booths.toLocaleString();
    document.getElementById('district-total-votes').textContent = totals.total_votes.toLocaleString();
    document.getElementById('district-winner').textContent = `${districtSummary.winner} +${districtSummary.margin.toLocaleString()}`;

    // Calculate percentages
    const dmkPct = (totals.dmk_votes / totals.total_votes * 100);
    const admkPct = (totals.aiadmk_votes / totals.total_votes * 100);
    const othersPct = (totals.others_votes / totals.total_votes * 100);

    // Update party bar
    document.getElementById('dmk-bar').style.width = `${dmkPct}%`;
    document.getElementById('admk-bar').style.width = `${admkPct}%`;
    document.getElementById('others-bar').style.width = `${othersPct}%`;

    document.getElementById('dmk-votes').textContent = `${totals.dmk_votes.toLocaleString()} (${dmkPct.toFixed(1)}%)`;
    document.getElementById('admk-votes').textContent = `${totals.aiadmk_votes.toLocaleString()} (${admkPct.toFixed(1)}%)`;
    document.getElementById('others-votes').textContent = `${totals.others_votes.toLocaleString()} (${othersPct.toFixed(1)}%)`;
}

function renderAreaCards() {
    const grid = document.getElementById('areas-grid');
    grid.innerHTML = '';

    districtSummary.areas.forEach(area => {
        const card = document.createElement('div');
        card.className = 'area-card';
        card.onclick = () => showBoothAnalysis(area.name);

        const winnerClass = area.winner.toLowerCase();
        const marginSign = area.winner === 'DMK' ? '+' : '-';

        card.innerHTML = `
            <div class="area-card-header">
                <h3>${area.name}</h3>
                <span class="area-card-ac">AC${area.ac_number}</span>
            </div>
            <span class="area-winner ${winnerClass}">${area.winner} ${marginSign}${area.margin.toLocaleString()}</span>
            <div class="area-stats">
                <div class="area-stat-row">
                    <span class="area-stat-label">Total Booths</span>
                    <span class="area-stat-value">${area.booths.toLocaleString()}</span>
                </div>
                <div class="area-stat-row">
                    <span class="area-stat-label">Total Votes</span>
                    <span class="area-stat-value">${area.total_votes.toLocaleString()}</span>
                </div>
                <div class="area-stat-row">
                    <span class="area-stat-label">DMK</span>
                    <span class="area-stat-value">${area.dmk_votes.toLocaleString()}</span>
                </div>
                <div class="area-stat-row">
                    <span class="area-stat-label">AIADMK</span>
                    <span class="area-stat-value">${area.aiadmk_votes.toLocaleString()}</span>
                </div>
            </div>
            <button class="analyze-btn">Analyze Booth Data →</button>
        `;

        grid.appendChild(card);
    });
}

// ===========================
// Constituency Management
// ===========================
function populateConstituencyDropdown() {
    const select = document.getElementById('constituency-select');
    select.innerHTML = '';

    masterData.districts.forEach(district => {
        district.constituencies.forEach(constituency => {
            if (constituency.total_booths > 0) {
                const option = document.createElement('option');
                option.value = constituency.data_file;
                option.textContent = `${constituency.name} (AC${constituency.ac_number})`;
                option.dataset.acNumber = constituency.ac_number;
                option.dataset.hasGeocoding = constituency.has_geocoding;
                select.appendChild(option);
            }
        });
    });

    // Load first constituency
    if (select.options.length > 0) {
        select.selectedIndex = 0;
        loadConstituency(select.value);
    }
}

async function loadConstituency(dataFile) {
    try {
        const response = await fetch(`data/${dataFile}`);
        if (!response.ok) throw new Error(`Failed to load ${dataFile}`);
        currentConstituency = await response.json();

        // Process booths
        allBooths = currentConstituency.booths.map((booth, index) => {
            // Simplify category inline to avoid reference errors
            const winner = booth.winner?.toUpperCase() || '';
            const marginPct = booth.margin_pct || 0;
            let category_simple = 'swing';
            if (marginPct > 10) {
                if (winner === 'DMK') category_simple = 'strong-dmk';
                else if (winner === 'AIADMK' || winner === 'ADMK') category_simple = 'strong-admk';
            }

            return {
                ...booth,
                id: index,
                booth_no: parseInt(booth.booth_no) || index + 1,
                station_no: parseInt(booth.station_no) || 0,
                category_simple
            };
        });

        filteredBooths = [...allBooths];

        // Reset sort to booth_no ascending
        currentSort = { column: 'booth_no', ascending: true };


        // Reset filter
        activeFilter = null;
        document.querySelectorAll('.stat-card.clickable').forEach(card => {
            card.classList.remove('active');
        });

        // Compute geohashes
        computeGeohashAreas();

        // Populate village filter
        populateVillageFilter();

        // Update stats
        updateStats();

        // Render table and map
        currentPage = 1;
        renderTable();
        renderGeohashAreas();

        console.log(`✅ Loaded ${currentConstituency.constituency}: ${allBooths.length} booths`);
    } catch (error) {
        console.error('Error loading constituency:', error);
    }
}

// ===========================
// Map Initialization
// ===========================
function initMap() {
    map = L.map('map', {
        center: [12.6149, 79.7594],
        zoom: 11,
        zoomControl: true
    });

    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap &copy; CARTO',
        subdomains: 'abcd',
        maxZoom: 19
    }).addTo(map);
}

// ===========================
// Category Simplification
// ===========================
function simplifyCategory(booth) {
    const winner = booth.winner?.toUpperCase() || '';
    const marginPct = booth.margin_pct || 0;

    if (marginPct > 10) {
        if (winner === 'DMK') return 'strong-dmk';
        if (winner === 'AIADMK' || winner === 'ADMK') return 'strong-admk';
    }

    return 'swing';
}

function getCategoryLabel(category) {
    const labels = {
        'strong-dmk': 'Strong DMK',
        'strong-admk': 'Strong ADMK',
        'swing': 'Swing'
    };
    return labels[category] || category;
}

// ===========================
// Geohash Computation
// ===========================
function computeGeohashAreas() {
    geohashAreas.clear();

    allBooths.forEach(booth => {
        if (!booth.lat || !booth.lng) return;

        const hash = geohash.encode(booth.lat, booth.lng, GEOHASH_PRECISION);

        if (!geohashAreas.has(hash)) {
            geohashAreas.set(hash, {
                hash,
                booths: [],
                dmk_votes: 0,
                aiadmk_votes: 0,
                others_votes: 0,
                bounds: geohash.decode_bbox(hash)
            });
        }

        const area = geohashAreas.get(hash);
        area.booths.push(booth);
        area.dmk_votes += booth.dmk_votes || 0;
        area.aiadmk_votes += booth.aiadmk_votes || 0;
        area.others_votes += booth.others_votes || 0;
    });

    // Determine dominant category
    geohashAreas.forEach(area => {
        const total = area.dmk_votes + area.aiadmk_votes;
        const dmkPct = total > 0 ? (area.dmk_votes / total) * 100 : 0;
        const aiadmkPct = total > 0 ? (area.aiadmk_votes / total) * 100 : 0;
        const margin = Math.abs(dmkPct - aiadmkPct);

        if (margin > 10) {
            area.category = dmkPct > aiadmkPct ? 'strong-dmk' : 'strong-admk';
        } else {
            area.category = 'swing';
        }

        // Add average swings for comparison mode
        area.avg_dmk_swing = area.booths.reduce((sum, b) => sum + (b.comparison?.dmk_swing || 0), 0) / area.booths.length;
        area.avg_aiadmk_swing = area.booths.reduce((sum, b) => sum + (b.comparison?.aiadmk_swing || 0), 0) / area.booths.length;
    });
}

// ===========================
// Geohash Map Rendering
// ===========================
function renderGeohashAreas() {
    geohashLayers.forEach(layer => map.removeLayer(layer));
    geohashLayers = [];

    const visibleHashes = new Set();
    filteredBooths.forEach(booth => {
        if (booth.lat && booth.lng) {
            const hash = geohash.encode(booth.lat, booth.lng, GEOHASH_PRECISION);
            visibleHashes.add(hash);
        }
    });

    visibleHashes.forEach(hash => {
        const area = geohashAreas.get(hash);
        if (!area) return;

        const bounds = area.bounds;
        const color = COLORS[area.category.replace('strong-', '')];
        const polygon = L.rectangle(
            [[bounds[0], bounds[1]], [bounds[2], bounds[3]]],
            {
                className: `geohash-area ${area.category}`,
                color: color,
                fillColor: color,
                fillOpacity: 0.3,
                weight: 2
            }
        );

        let popupContent = `
            <div style="font-size: 0.875rem;">
                <strong>2021: ${getCategoryLabel(area.category)}</strong><br>
                Booths: ${area.booths.length}<br>
                DMK: ${area.dmk_votes.toLocaleString()}<br>
                ADMK: ${area.aiadmk_votes.toLocaleString()}<br>
        `;

        if (area.avg_dmk_swing !== undefined) {
            popupContent += `
                 <hr style="margin: 5px 0; border: 0; border-top: 1px solid var(--border-color);">
                 <strong>16-21 Comparison:</strong><br>
                 Avg DMK Swing: <span style="color: ${area.avg_dmk_swing > 0 ? 'var(--dmk-color)' : 'inherit'}">${area.avg_dmk_swing > 0 ? '+' : ''}${area.avg_dmk_swing.toFixed(2)}%</span><br>
                 Avg Turnout Δ: ${area.avg_turnout_change > 0 ? '+' : ''}${area.avg_turnout_change.toFixed(2)}%
             `;
        }
        popupContent += '</div>';

        polygon.bindPopup(popupContent);

        polygon.on('click', () => filterByGeohash(hash));

        polygon.addTo(map);
        geohashLayers.push(polygon);
    });
}

function filterByGeohash(hash) {
    const area = geohashAreas.get(hash);
    if (!area) return;

    const boothIds = new Set(area.booths.map(b => b.id));
    filteredBooths = allBooths.filter(b => boothIds.has(b.id));

    currentPage = 1;
    renderTable();
    updateStats();
}

// ===========================
// Table Rendering
// ===========================
function renderTable() {
    const tbody = document.getElementById('table-body');
    tbody.innerHTML = '';

    const sorted = [...filteredBooths].sort((a, b) => {
        const col = currentSort.column;
        let aVal = a[col];
        let bVal = b[col];

        if (typeof aVal === 'number' && typeof bVal === 'number') {
            return currentSort.ascending ? aVal - bVal : bVal - aVal;
        }

        aVal = String(aVal || '').toLowerCase();
        bVal = String(bVal || '').toLowerCase();

        if (currentSort.ascending) {
            return aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
        } else {
            return aVal > bVal ? -1 : aVal < bVal ? 1 : 0;
        }
    });

    const start = (currentPage - 1) * ITEMS_PER_PAGE;
    const end = start + ITEMS_PER_PAGE;
    const pageBooths = sorted.slice(start, end);

    pageBooths.forEach(booth => {
        const row = document.createElement('tr');
        row.className = booth.category_simple;
        row.dataset.boothId = booth.id;

        if (booth.id === selectedBoothId) {
            row.classList.add('selected');
        }

        // Location display with lat/lng and building
        let locationHTML = booth.village || 'N/A';
        if (booth.lat && booth.lng) {
            locationHTML += `<br><small style="color: var(--text-muted);">📍 ${booth.lat.toFixed(4)}, ${booth.lng.toFixed(4)}</small>`;
        }

        // Unified Table Row
        const comp = booth.comparison || {};
        const dmkSwing = comp.dmk_swing !== undefined ? ` <small style="color: ${comp.dmk_swing > 0 ? 'var(--dmk-color)' : 'var(--text-muted)'}">(${comp.dmk_swing > 0 ? '+' : ''}${comp.dmk_swing}%)</small>` : '';
        const admkSwing = comp.aiadmk_swing !== undefined ? ` <small style="color: ${comp.aiadmk_swing > 0 ? 'var(--aiadmk-color)' : 'var(--text-muted)'}">(${comp.aiadmk_swing > 0 ? '+' : ''}${comp.aiadmk_swing}%)</small>` : '';

        row.innerHTML = `
            <td><strong>${booth.booth_no}</strong></td>
            <td>${locationHTML}</td>
            <td class="vote-count">${(booth.dmk_votes || 0).toLocaleString()}${dmkSwing}</td>
            <td class="vote-count">${(booth.aiadmk_votes || 0).toLocaleString()}${admkSwing}</td>
            <td class="vote-count">${(booth.others_votes || 0).toLocaleString()}</td>
            <td><span class="category-badge ${booth.category_simple}">${getCategoryLabel(booth.category_simple)}</span></td>
        `;

        row.addEventListener('click', () => selectBooth(booth));
        tbody.appendChild(row);
    });

    updatePagination(sorted.length);
}

function selectBooth(booth) {
    selectedBoothId = booth.id;

    document.querySelectorAll('#booths-table tbody tr').forEach(row => {
        row.classList.remove('selected');
    });
    document.querySelector(`tr[data-booth-id="${booth.id}"]`)?.classList.add('selected');

    if (booth.lat && booth.lng) {
        map.setView([booth.lat, booth.lng], 15);
    }
}

// ===========================
// Pagination
// ===========================
function updatePagination(totalItems) {
    const totalPages = Math.ceil(totalItems / ITEMS_PER_PAGE);

    document.getElementById('page-info').textContent = `Page ${currentPage} of ${totalPages}`;
    document.getElementById('prev-page').disabled = currentPage === 1;
    document.getElementById('next-page').disabled = currentPage === totalPages || totalPages === 0;
}

// ===========================
// Filters
// ===========================
function populateVillageFilter() {
    const villages = [...new Set(allBooths.map(b => b.village))].filter(v => v && v.trim() !== '');
    villages.sort();

    const select = document.getElementById('filter-village');
    select.innerHTML = '<option value="all">All Villages</option>';
    villages.forEach(village => {
        const option = document.createElement('option');
        option.value = village;
        option.textContent = village;
        select.appendChild(option);
    });
}

function applyFilters() {
    const village = document.getElementById('filter-village').value;
    const search = document.getElementById('search-input').value.toLowerCase();

    filteredBooths = allBooths.filter(booth => {
        if (village !== 'all' && booth.village !== village) return false;

        // Category filter from active stat card
        if (activeFilter && booth.category_simple !== activeFilter) return false;

        if (search) {
            const searchMatch =
                booth.booth_no?.toString().toLowerCase().includes(search) ||
                booth.village?.toLowerCase().includes(search) ||
                booth.building?.toLowerCase().includes(search);
            if (!searchMatch) return false;
        }

        return true;
    });

    currentPage = 1;
    renderTable();
    renderGeohashAreas();
    updateStats();
}

// ===========================
// Stats Update
// ===========================
function updateStats() {
    const strongDmk = allBooths.filter(b => b.category_simple === 'strong-dmk').length;
    const strongAdmk = allBooths.filter(b => b.category_simple === 'strong-admk').length;
    const swing = allBooths.filter(b => b.category_simple === 'swing').length;

    document.getElementById('dmk-won').textContent = strongDmk;
    document.getElementById('aiadmk-won').textContent = strongAdmk;
    document.getElementById('swing-count').textContent = swing;

    // Unified Labels with Swing Context
    const summary = currentConstituency?.summary || {};
    if (summary.avg_dmk_swing !== undefined) {
        document.querySelectorAll('.stat-card.dmk .stat-label')[0].innerHTML = `Strong DMK <small style="display:block; opacity:0.8;">Avg Swing: ${summary.avg_dmk_swing > 0 ? '+' : ''}${summary.avg_dmk_swing.toFixed(1)}%</small>`;
        document.querySelectorAll('.stat-card.aiadmk .stat-label')[0].innerHTML = `Strong ADMK <small style="display:block; opacity:0.8;">Avg Swing: ${summary.avg_aiadmk_swing > 0 ? '+' : ''}${summary.avg_aiadmk_swing.toFixed(1)}%</small>`;
        document.querySelectorAll('.stat-card.swing .stat-label')[0].innerHTML = `Swing <small style="display:block; opacity:0.8;">Turnout: ${summary.avg_turnout_change > 0 ? '+' : ''}${summary.avg_turnout_change.toFixed(1)}%</small>`;
    } else {
        document.querySelectorAll('.stat-card.dmk .stat-label')[0].textContent = 'Strong DMK';
        document.querySelectorAll('.stat-card.aiadmk .stat-label')[0].textContent = 'Strong ADMK';
        document.querySelectorAll('.stat-card.swing .stat-label')[0].textContent = 'Swing';
    }

    // Total booths always shows constituency total
    document.getElementById('total-booths').textContent = currentConstituency?.summary.total_booths || allBooths.length;
}

// ===========================
// Event Listeners
// ===========================
function setupEventListeners() {
    // Back button
    document.getElementById('back-btn').addEventListener('click', () => {
        showDistrictOverview();
    });

    // Constituency selector (for booth analysis view)
    const constituencySelect = document.getElementById('constituency-select');
    if (constituencySelect) {
        constituencySelect.addEventListener('change', (e) => {
            loadConstituency(e.target.value);
        });
    }

    // Area selector
    const areaSelect = document.getElementById('area-select');
    if (areaSelect) {
        areaSelect.addEventListener('change', (e) => {
            const areaName = e.target.value;
            if (areaName) {
                showBoothAnalysis(areaName);
            }
        });
    }


    // Clickable stat cards
    document.querySelectorAll('.stat-card.clickable').forEach(card => {
        card.addEventListener('click', () => {
            const filter = card.dataset.filter;

            // Toggle filter
            if (activeFilter === filter) {
                activeFilter = null;
                card.classList.remove('active');
            } else {
                // Remove active from all cards
                document.querySelectorAll('.stat-card.clickable').forEach(c => c.classList.remove('active'));
                activeFilter = filter;
                card.classList.add('active');
            }

            applyFilters();
        });
    });

    // Total Booths stat card - reset all filters
    const totalBoothsCard = document.querySelector('.stat-card:not(.clickable)');
    if (totalBoothsCard) {
        totalBoothsCard.style.cursor = 'pointer';
        totalBoothsCard.addEventListener('click', () => {
            // Reset all filters
            activeFilter = null;
            document.querySelectorAll('.stat-card.clickable').forEach(c => c.classList.remove('active'));
            document.getElementById('filter-village').value = 'all';
            filteredBooths = [...allBooths];
            currentPage = 1;
            renderTable();
            renderGeohashAreas();
        });
    }

    // Village filter
    document.getElementById('filter-village').addEventListener('change', applyFilters);

    // Search with debounce
    let searchTimeout;
    document.getElementById('search-input').addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(applyFilters, 300);
    });

    // Pagination
    document.getElementById('prev-page').addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            renderTable();
        }
    });

    document.getElementById('next-page').addEventListener('click', () => {
        const totalPages = Math.ceil(filteredBooths.length / ITEMS_PER_PAGE);
        if (currentPage < totalPages) {
            currentPage++;
            renderTable();
        }
    });

    // Table sorting
    document.querySelectorAll('#booths-table th[data-sort]').forEach(th => {
        th.addEventListener('click', () => {
            const column = th.dataset.sort;
            if (currentSort.column === column) {
                currentSort.ascending = !currentSort.ascending;
            } else {
                currentSort.column = column;
                currentSort.ascending = true;
            }
            renderTable();
        });
    });
}

// ===========================
// Initialize on DOM Ready
// ===========================
document.addEventListener('DOMContentLoaded', init);
