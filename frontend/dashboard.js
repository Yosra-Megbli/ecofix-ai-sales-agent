// Client script for Ecofix Dashboard Analytics

document.addEventListener('DOMContentLoaded', () => {
    // API Endpoint for Stats
    const statsUrl = `${window.location.origin}/dashboard/stats`;

    // DOM Elements
    const valTotalLeads = document.getElementById('val-total-leads');
    const valTotalConv = document.getElementById('val-total-conv');
    const valConvRate = document.getElementById('val-conv-rate');
    const errorBanner = document.getElementById('error-banner-id');
    const errorText = document.getElementById('error-text-id');
    const chartLoader = document.getElementById('chart-loader-id');
    const pipelineTbody = document.getElementById('pipeline-tbody-id');
    const statusChartCanvas = document.getElementById('statusChart');

    // Human-readable status mapping (with translation/formatting)
    const statusLabels = {
        "New": "Nouveau lead (New)",
        "Contacted": "Contacté (Contacted)",
        "Replied": "A répondu (Replied)",
        "Qualified": "Qualifié (Qualified)",
        "Appointment": "Rdv fixé (Appointment)",
        "Contract Sent": "Contrat envoyé (Contract Sent)",
        "Sold": "Contrat signé (Sold) 🎉",
        "Rejected": "Perdu / Rejeté (Rejected) ❌"
    };

    // Logical pipeline order for sorting and displaying charts/tables
    const pipelineOrder = ["New", "Contacted", "Replied", "Qualified", "Appointment", "Contract Sent", "Sold", "Rejected"];

    // Default status colors for chart
    const statusColors = {
        "New": "rgba(144, 164, 174, 0.7)",      // Grey-blue
        "Contacted": "rgba(2, 136, 209, 0.7)",    // Light-blue
        "Replied": "rgba(0, 150, 136, 0.7)",      // Teal
        "Qualified": "rgba(76, 175, 80, 0.7)",    // Green
        "Appointment": "rgba(255, 152, 0, 0.7)",  // Orange
        "Contract Sent": "rgba(156, 39, 176, 0.7)", // Purple
        "Sold": "rgba(46, 125, 50, 0.9)",         // Dark Green (Success)
        "Rejected": "rgba(239, 83, 80, 0.8)"      // Soft Red (Failure)
    };

    const statusBorderColors = {
        "New": "#90a4ae",
        "Contacted": "#0288d1",
        "Replied": "#009688",
        "Qualified": "#4caf50",
        "Appointment": "#ff9800",
        "Contract Sent": "#9c27b0",
        "Sold": "#2e7d32",
        "Rejected": "#ef5350"
    };

    // Remove skeleton class and update text
    function updateMetric(element, value, suffix = '') {
        element.classList.remove('loading-skeleton');
        element.textContent = `${value}${suffix}`;
    }

    // Load Dashboard Stats
    async function loadStats() {
        try {
            const response = await fetch(statsUrl, {
                headers: {
                    'Accept': 'application/json'
                }
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `Server error: ${response.statusText}`);
            }

            const data = await response.json();

            // 1. Update metric cards
            updateMetric(valTotalLeads, data.total_leads);
            updateMetric(valTotalConv, data.total_conversations);
            updateMetric(valConvRate, data.conversion_rate, '%');

            // 2. Build Pipeline Data arrays
            const counts = data.status_counts || {};
            
            // Build arrays for Chart and Table following pipeline order
            const chartLabels = [];
            const chartData = [];
            const chartBgColors = [];
            const chartBorders = [];
            
            let tableHtml = "";

            pipelineOrder.forEach(statusKey => {
                const count = counts[statusKey] || 0;
                const label = statusLabels[statusKey] || statusKey;
                
                // Add to Chart datasets
                chartLabels.push(label);
                chartData.push(count);
                chartBgColors.push(statusColors[statusKey] || "rgba(0, 0, 0, 0.1)");
                chartBorders.push(statusBorderColors[statusKey] || "#cfd8dc");

                // Append row to Table
                tableHtml += `
                    <tr>
                        <td>
                            <span class="status-indicator-dot" style="background-color: ${statusBorderColors[statusKey] || '#999'}"></span>
                            ${label}
                        </td>
                        <td class="text-right font-semibold">${count}</td>
                    </tr>
                `;
            });

            // Append any extra statuses that might be custom defined in Airtable
            Object.keys(counts).forEach(statusKey => {
                if (!pipelineOrder.includes(statusKey)) {
                    const count = counts[statusKey] || 0;
                    chartLabels.push(statusKey);
                    chartData.push(count);
                    chartBgColors.push("rgba(78, 93, 108, 0.7)");
                    chartBorders.push("#4e5d6c");

                    tableHtml += `
                        <tr>
                            <td>
                                <span class="status-indicator-dot" style="background-color: #4e5d6c"></span>
                                ${statusKey}
                            </td>
                            <td class="text-right font-semibold">${count}</td>
                        </tr>
                    `;
                }
            });

            pipelineTbody.innerHTML = tableHtml;

            // 3. Render Chart.js Graph
            renderChart(chartLabels, chartData, chartBgColors, chartBorders);

        } catch (error) {
            console.error('[Dashboard] Error fetching analytics stats:', error);
            
            // Show Error Banner
            errorText.textContent = `Erreur : ${error.message}`;
            errorBanner.classList.remove('hidden');
            
            // Remove skeleton from cards and set error indicators
            [valTotalLeads, valTotalConv, valConvRate].forEach(el => {
                el.classList.remove('loading-skeleton');
                el.textContent = "N/A";
                el.style.color = "var(--text-light)";
            });

            // Clear table loader
            pipelineTbody.innerHTML = `<tr><td colspan="2" class="text-center text-red">Erreur de chargement des données.</td></tr>`;
            
            // Stop Chart loader with error message
            chartLoader.innerHTML = `<div class="chart-error"><i class="fa-solid fa-triangle-exclamation"></i><br>Données indisponibles</div>`;
        }
    }

    // Function to render Chart.js chart
    function renderChart(labels, data, bgColors, borderColors) {
        // Hide loader and show canvas
        chartLoader.classList.add('hidden');
        statusChartCanvas.classList.remove('hidden');

        // Create Chart
        new Chart(statusChartCanvas, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Nombre de leads',
                    data: data,
                    backgroundColor: bgColors,
                    borderColor: borderColors,
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y', // Horizontal bars
                plugins: {
                    legend: {
                        display: false // No legend needed for single dataset
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return ` Leads: ${context.parsed.x}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0 // Only whole integers on X axis
                        },
                        grid: {
                            color: '#eceff1'
                        }
                    },
                    y: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }

    // Initialize Loading
    loadStats();
});
