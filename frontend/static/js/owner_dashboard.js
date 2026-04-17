// owner_dashboard.js — House Owner Dashboard Charts & Data Loader

let usageChart, solarChart, priceChart;

async function loadDashboard() {
    try {
        const input = document.getElementById('consumer_id_input');
        const meter = input ? input.value.trim() : '';
        
        // Show loading state if manual search
        if (meter) {
            console.log("Loading dashboard for meter:", meter);
        }

        const url = meter ? `/api/house/dashboard?meter=${meter}` : '/api/house/dashboard';
        const res = await fetch(url);
        const d = await res.json();
        
        if (!d.success) { 
            console.error('Dashboard API error:', d.message);
            if (meter) alert('Error: ' + d.message); 
            return; 
        }

        if (d.meter) {
             document.getElementById('active_meter').textContent = d.meter;
             if (input && !input.value) input.value = d.meter;
        }

        // Make content visible once loaded
        const content = document.getElementById('dashboard_content');
        if (content) content.style.display = 'block';

        populateMetrics(d);
        renderUsageChart(d.usage);
        renderSolarChart(d.solar);
        renderPriceChart(d.price_prediction);
        populateGrid(d.grid);
        populateBill(d.bill);
        populateSubsidy(d.subsidy);
        populateSavings(d.savings);
    } catch (err) {
        console.error('Dashboard load error:', err);
    }
}

function fmt(n, decimals = 1) { return parseFloat(n).toFixed(decimals); }
function fmtRs(n) { return '₹' + parseFloat(n).toLocaleString('en-IN', {minimumFractionDigits: 0, maximumFractionDigits: 0}); }

function populateMetrics(d) {
    const elUsage = document.getElementById('today_usage');
    const elSolar = document.getElementById('solar_generated');
    const elSavings = document.getElementById('money_saved');
    const elBill = document.getElementById('current_bill');

    if (elUsage) elUsage.textContent = fmt(d.usage.today) + ' kWh';
    if (elSolar) elSolar.textContent = fmt(d.solar.today) + ' kWh';
    if (elSavings) elSavings.textContent = fmtRs(d.savings.money_saved);
    if (elBill) elBill.textContent = fmtRs(d.bill.final_bill);
}

function renderUsageChart(usage) {
    const ctx = document.getElementById('usageChart').getContext('2d');
    if (usageChart) usageChart.destroy();
    usageChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Today', 'This Week', 'This Month'],
            datasets: [{
                label: 'Electricity Usage (kWh)',
                data: [usage.today, usage.week, usage.month],
                backgroundColor: ['rgba(0,229,255,0.6)', 'rgba(0,229,255,0.4)', 'rgba(0,229,255,0.2)'],
                borderColor: ['rgba(0,229,255,1)', 'rgba(0,229,255,0.8)', 'rgba(0,229,255,0.6)'],
                borderWidth: 2,
                borderRadius: 8,
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#b0c4d8' } },
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#b0c4d8', callback: v => v + ' kWh' } }
            }
        }
    });
}

function renderSolarChart(solar) {
    const ctx = document.getElementById('solarChart').getContext('2d');
    if (solarChart) solarChart.destroy();
    solarChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Solar ☀️', 'Grid 🔌'],
            datasets: [{
                data: [solar.contribution_percent, solar.grid_percent],
                backgroundColor: ['rgba(255,200,0,0.75)', 'rgba(0,229,255,0.3)'],
                borderColor: ['rgba(255,200,0,1)', 'rgba(0,229,255,0.6)'],
                borderWidth: 2,
                hoverOffset: 8
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            cutout: '68%',
            plugins: {
                legend: { position: 'bottom', labels: { color: '#b0c4d8', padding: 16, font: { size: 12 } } },
                tooltip: { callbacks: { label: ctx => ` ${ctx.label}: ${ctx.parsed}%` } }
            }
        }
    });
    const elPct = document.getElementById('solar_pct');
    if (elPct) elPct.textContent = fmt(solar.contribution_percent, 0) + '%';
}

function renderPriceChart(prediction) {
    const ctx = document.getElementById('priceChart').getContext('2d');
    if (priceChart) priceChart.destroy();
    const hours = prediction.map(p => p.hour + ':00');
    const prices = prediction.map(p => p.price_rs);
    const minPrice = Math.min(...prices);
    const minHour = hours[prices.indexOf(minPrice)];

    priceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: hours,
            datasets: [{
                label: 'Price (₹/kWh)',
                data: prices,
                borderColor: 'rgba(57,255,20,0.9)',
                backgroundColor: 'rgba(57,255,20,0.06)',
                borderWidth: 2.5,
                pointRadius: 3,
                pointBackgroundColor: 'rgba(57,255,20,0.9)',
                fill: true, tension: 0.4
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { callbacks: { label: ctx => ` ₹${ctx.parsed.y}/kWh` } }
            },
            scales: {
                x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#b0c4d8', maxRotation: 45, font: { size: 10 } } },
                y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#b0c4d8', callback: v => '₹' + v } }
            }
        }
    });
    document.getElementById('best-time').textContent = minHour;
    document.getElementById('best-price').textContent = '₹' + minPrice;
}

function populateGrid(grid) {
    const elImpKwh = document.getElementById('grid_import_kwh');
    const elExpKwh = document.getElementById('grid_export_kwh');
    const elImpCost = document.getElementById('grid_import_cost');
    const elExpCredit = document.getElementById('grid_export_credit');
    const elFinal = document.getElementById('grid_final_bill');

    if (elImpKwh) elImpKwh.textContent = fmt(grid.import_kwh) + ' kWh';
    if (elExpKwh) elExpKwh.textContent = fmt(grid.export_kwh) + ' kWh';
    if (elImpCost) elImpCost.textContent = fmtRs(grid.import_cost);
    if (elExpCredit) elExpCredit.textContent = fmtRs(grid.export_credit);
    if (elFinal) elFinal.textContent = fmtRs(grid.final_bill);
}

function populateBill(bill) {
    const elImp = document.getElementById('bill_import_cost');
    const elExp = document.getElementById('bill_export_credit');
    const elFinal = document.getElementById('bill_final');
    const elDue = document.getElementById('bill_due');

    if (elImp) elImp.textContent = fmtRs(bill.grid_import_cost);
    if (elExp) elExp.textContent = fmtRs(bill.export_credit);
    if (elFinal) elFinal.textContent = fmtRs(bill.final_bill);
    
    if (elDue) {
        const due = new Date(bill.due_date);
        elDue.textContent = due.toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' });
    }
}

function populateSubsidy(sub) {
    const elCap = document.getElementById('sub_capacity');
    const elAmt = document.getElementById('sub_amount');
    const elScheme = document.getElementById('sub_scheme');

    if (elCap) elCap.textContent = sub.capacity_kw + ' kW';
    if (elAmt) elAmt.textContent = fmtRs(sub.subsidy_amount);
    if (elScheme) elScheme.textContent = sub.scheme;
}

function populateSavings(sav) {
    const elElec = document.getElementById('sav_elec');
    const elMoney = document.getElementById('sav_money');
    const elBase = document.getElementById('sav_base');
    const elOpt = document.getElementById('sav_opt');

    if (elElec) elElec.textContent = fmt(sav.electricity_saved) + ' kWh';
    if (elMoney) elMoney.textContent = fmtRs(sav.money_saved);
    if (elBase) elBase.textContent = fmt(sav.baseline_usage) + ' kWh';
    if (elOpt) elOpt.textContent = fmt(sav.optimized_usage) + ' kWh';
}

function payBill() {
    window.open("https://portal.apspdcl.in/OnlinePayment", "_blank");
}

async function downloadTelemetry() {
    try {
        const input = document.getElementById('consumer_id_input');
        const meter = input ? input.value.trim() : '';
        const url = meter ? `/api/house/export_telemetry?meter=${meter}` : '/api/house/export_telemetry';

        console.log("Downloading telemetry for:", meter || "Session Meter");
        
        const res = await fetch(url);
        if (!res.ok) {
            const err = await res.json();
            alert('Export failed: ' + (err.message || 'Unknown error'));
            return;
        }
        const blob = await res.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = `telemetry_export.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(downloadUrl);
        document.body.removeChild(a);
    } catch (err) {
        console.error('Download error:', err);
        alert('Failed to download telemetry. Please try again.');
    }
}

document.addEventListener('DOMContentLoaded', loadDashboard);
