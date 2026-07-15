// -------------------------------------------------------------
// AlphaDoc-Analytics Frontend Application Logic
// -------------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
    // API Configuration
    const API_BASE_URL = "http://127.0.0.1:8000";

    // DOM Elements
    const dropzone = document.getElementById("dropzone");
    const fileInput = document.getElementById("file-input");
    const btnLoadDemo = document.getElementById("btn-load-demo");
    const uploadStatus = document.getElementById("upload-status");
    const riskList = document.getElementById("risk-list");
    
    const metaCompany = document.getElementById("meta-company");
    const metaPeriod = document.getElementById("meta-period");
    const metaSentiment = document.getElementById("meta-sentiment");

    const kpiRevVal = document.getElementById("kpi-rev-val");
    const kpiRevChange = document.getElementById("kpi-rev-change");
    const kpiRevProj = document.getElementById("kpi-rev-proj");
    const kpiRevTrend = document.getElementById("kpi-rev-trend");

    const kpiMarginVal = document.getElementById("kpi-margin-val");
    const kpiMarginChange = document.getElementById("kpi-margin-change");
    const kpiMarginProj = document.getElementById("kpi-margin-proj");
    const kpiMarginTrend = document.getElementById("kpi-margin-trend");

    const kpiNetVal = document.getElementById("kpi-net-val");
    const kpiNetChange = document.getElementById("kpi-net-change");
    const kpiNetProj = document.getElementById("kpi-net-proj");
    const kpiNetTrend = document.getElementById("kpi-net-trend");

    const chatMessages = document.getElementById("chat-messages");
    const chatInput = document.getElementById("chat-input");
    const btnSendChat = document.getElementById("btn-send-chat");

    // Global Chart Instance Reference
    let kpiChart = null;

    // --- Drag & Drop Handlers ---
    dropzone.addEventListener("click", () => fileInput.click());

    dropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropzone.classList.add("active");
    });

    dropzone.addEventListener("dragleave", () => {
        dropzone.classList.remove("active");
    });

    dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropzone.classList.remove("active");
        if (e.dataTransfer.files.length > 0) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files[0]);
        }
    });

    // --- Load Demo Dataset ---
    btnLoadDemo.addEventListener("click", async () => {
        setLoadingState(true, "Extracting demo records...");
        try {
            const response = await fetch(`${API_BASE_URL}/api/demo`);
            if (!response.ok) throw new Error("Demo loader returned connection issue.");
            const data = await response.json();
            updateDashboard(data);
            addSystemChatMessage("Demo analysis loaded. You can now chat with the simulated financial analyst.");
        } catch (error) {
            setLoadingState(false);
            uploadStatus.innerHTML = `<span style="color: var(--accent);">Failed to load demo data: ${error.message}. Is backend FastAPI running?</span>`;
        }
    });

    // --- File Upload Execution ---
    async function handleFileUpload(file) {
        if (!file.name.toLowerCase().endswith(".pdf")) {
            uploadStatus.innerHTML = '<span style="color: var(--accent);">Error: Only PDF documents are supported.</span>';
            return;
        }

        const formData = new FormData();
        formData.append("file", file);

        setLoadingState(true, `Uploading ${file.name}...`);
        try {
            const response = await fetch(`${API_BASE_URL}/api/upload`, {
                method: "POST",
                body: formData
            });
            
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || "Server pipeline error");
            }
            
            const data = await response.json();
            updateDashboard(data);
            addSystemChatMessage(`Successfully analyzed ${file.name}. Chat agent is ready.`);
        } catch (error) {
            setLoadingState(false);
            uploadStatus.innerHTML = `<span style="color: var(--accent);">Processing Failed: ${error.message}</span>`;
        }
    }

    // Helper: loading indicators
    function setLoadingState(isLoading, message = "") {
        if (isLoading) {
            uploadStatus.innerHTML = `<span style="color: var(--primary); animation: pulse 1.5s infinite;">⌛ ${message}</span>`;
            dropzone.style.pointerEvents = "none";
            dropzone.style.opacity = "0.6";
            btnLoadDemo.disabled = true;
        } else {
            uploadStatus.innerHTML = "";
            dropzone.style.pointerEvents = "all";
            dropzone.style.opacity = "1";
            btnLoadDemo.disabled = false;
        }
    }

    // --- Chat Integration ---
    btnSendChat.addEventListener("click", executeChatQuery);
    chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") executeChatQuery();
    });

    async function executeChatQuery() {
        const query = chatInput.value.trim();
        if (!query) return;

        // Render User Message
        addUserChatMessage(query);
        chatInput.value = "";
        chatInput.disabled = true;
        btnSendChat.disabled = true;

        try {
            const response = await fetch(`${API_BASE_URL}/api/chat`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: query })
            });
            const data = await response.json();
            addSystemChatMessage(data.response, data.thought_log);
        } catch (error) {
            addSystemChatMessage("Failed to retrieve query response. Verify server status.");
        } finally {
            chatInput.disabled = false;
            btnSendChat.disabled = false;
            chatInput.focus();
        }
    }

    function addUserChatMessage(text) {
        const msgDiv = document.createElement("div");
        msgDiv.className = "message user-message";
        msgDiv.innerHTML = `
            <span class="message-sender">User</span>
            <div class="message-text">${escapeHTML(text)}</div>
        `;
        chatMessages.appendChild(msgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function addSystemChatMessage(text, thoughtLog = null) {
        const msgDiv = document.createElement("div");
        msgDiv.className = "message system-message";
        
        let thoughtHTML = "";
        if (thoughtLog && thoughtLog.length > 0) {
            thoughtHTML = `
                <details class="thought-trace">
                    <summary>🛠️ View Agent Thought Trace (${thoughtLog.length} steps)</summary>
                    <pre class="thought-log-pre">${escapeHTML(thoughtLog.join("\n"))}</pre>
                </details>
            `;
        }

        msgDiv.innerHTML = `
            <span class="message-sender">Agent Network</span>
            ${thoughtHTML}
            <div class="message-text">${formatMarkdown(text)}</div>
        `;
        chatMessages.appendChild(msgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Helper: basic string sanitization
    function escapeHTML(str) {
        return str.replace(/[&<>'"]/g, 
            tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
        );
    }

    // Helper: parse bold markdown syntax in responses
    function formatMarkdown(text) {
        let formatted = escapeHTML(text);
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        formatted = formatted.replace(/\n/g, '<br>');
        return formatted;
    }

    // String endsWith fallback
    if (!String.prototype.endswith) {
        String.prototype.endswith = function(searchString, position) {
            const subjectString = this.toString();
            if (position === undefined || position > subjectString.length) {
                position = subjectString.length;
            }
            position -= searchString.length;
            const lastIndex = subjectString.indexOf(searchString, position);
            return lastIndex !== -1 && lastIndex === position;
        };
    }

    // --- Update Dashboard Elements ---
    function updateDashboard(data) {
        setLoadingState(false);
        uploadStatus.innerHTML = `<span style="color: var(--secondary);">✓ Analysis Complete (${data.raw_text_length} characters parsed)</span>`;
        
        // 1. Metadata
        metaCompany.innerText = data.company_name;
        metaPeriod.innerText = `${data.historical[0].period} - ${data.historical[data.historical.length - 1].period}`;
        
        const sentimentInfo = data.sentiment;
        metaSentiment.innerText = `${sentimentInfo.classification} (${sentimentInfo.score})`;
        
        // Adjust badge coloring based on classification
        metaSentiment.className = "meta-val sentiment-badge";
        if (sentimentInfo.classification.toLowerCase().includes("optimistic") || sentimentInfo.classification.toLowerCase().includes("positive")) {
            metaSentiment.style.borderColor = "rgba(16, 185, 129, 0.4)";
            metaSentiment.style.color = "var(--secondary)";
            metaSentiment.style.background = "var(--secondary-glow)";
        } else {
            metaSentiment.style.borderColor = "var(--border-color-active)";
            metaSentiment.style.color = "var(--primary)";
            metaSentiment.style.background = "var(--primary-glow)";
        }

        // 2. Risk lists
        riskList.innerHTML = "";
        data.risks.forEach(risk => {
            const li = document.createElement("li");
            li.innerText = risk;
            riskList.appendChild(li);
        });

        // 3. KPI Cards
        const lastHist = data.historical[data.historical.length - 1];
        
        // Revenue Card
        kpiRevVal.innerText = `$${lastHist.revenue}M`;
        kpiRevChange.innerText = `${lastHist.revenue_growth_qoq >= 0 ? '▲' : '▼'} ${Math.abs(lastHist.revenue_growth_qoq)}% QoQ`;
        kpiRevChange.style.color = lastHist.revenue_growth_qoq >= 0 ? "var(--secondary)" : "var(--accent)";
        kpiRevProj.innerText = `$${data.forecasts.revenue.predicted}M`;
        kpiRevTrend.innerText = `Slope: ${data.forecasts.revenue.trend_slope >= 0 ? '+' : ''}${data.forecasts.revenue.trend_slope}`;

        // Operating Margin Card
        kpiMarginVal.innerText = `${lastHist.operating_margin}%`;
        const marginDiff = (lastHist.operating_margin - data.historical[0].operating_margin).toFixed(1);
        kpiMarginChange.innerText = `${marginDiff >= 0 ? '▲' : '▼'} ${Math.abs(marginDiff)}% delta`;
        kpiMarginChange.style.color = marginDiff >= 0 ? "var(--secondary)" : "var(--accent)";
        kpiMarginProj.innerText = `${data.forecasts.operating_margin.predicted}%`;
        kpiMarginTrend.innerText = `Slope: ${data.forecasts.operating_margin.trend_slope >= 0 ? '+' : ''}${data.forecasts.operating_margin.trend_slope}`;

        // Net Income Card
        kpiNetVal.innerText = `$${lastHist.net_income}M`;
        kpiNetChange.innerText = `${lastHist.net_income_growth_qoq >= 0 ? '▲' : '▼'} ${Math.abs(lastHist.net_income_growth_qoq)}% QoQ`;
        kpiNetChange.style.color = lastHist.net_income_growth_qoq >= 0 ? "var(--secondary)" : "var(--accent)";
        kpiNetProj.innerText = `$${data.forecasts.net_income.predicted}M`;
        kpiNetTrend.innerText = `Slope: ${data.forecasts.net_income.trend_slope >= 0 ? '+' : ''}${data.forecasts.net_income.trend_slope}`;

        // 4. Render Chart
        renderVisualCharts(data);

        // Enable Chat Input
        chatInput.removeAttribute("disabled");
        btnSendChat.removeAttribute("disabled");
    }

    // --- Chart.js Visual Configuration ---
    function renderVisualCharts(data) {
        const ctx = document.getElementById("kpiChart").getContext("2d");
        
        // Destroy existing chart if present to prevent overlap bugs
        if (kpiChart) {
            kpiChart.destroy();
        }

        const labels = data.historical.map(item => item.period);
        labels.push(`${data.next_period} (Forecast)`);

        const revHist = data.historical.map(item => item.revenue);
        const netHist = data.historical.map(item => item.net_income);
        const marginHist = data.historical.map(item => item.operating_margin);

        // Append predictions
        const revForecastSeries = [...revHist.map(() => null), data.forecasts.revenue.predicted];
        const netForecastSeries = [...netHist.map(() => null), data.forecasts.net_income.predicted];
        const marginForecastSeries = [...marginHist.map(() => null), data.forecasts.operating_margin.predicted];

        // Prepare standard bounds arrays for confidence intervals
        const revLowerBounds = [...revHist.map(() => null), data.forecasts.revenue.lower_95];
        const revUpperBounds = [...revHist.map(() => null), data.forecasts.revenue.upper_95];

        kpiChart = new Chart(ctx, {
            type: "bar",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: "Revenue ($M)",
                        data: [...revHist, null],
                        backgroundColor: "rgba(139, 92, 246, 0.4)",
                        borderColor: "rgba(139, 92, 246, 0.8)",
                        borderWidth: 1,
                        yAxisID: "y-axis-kpi",
                        order: 3
                    },
                    {
                        label: "Revenue Forecast ($M)",
                        data: revForecastSeries,
                        backgroundColor: "rgba(244, 63, 94, 0.5)",
                        borderColor: "rgba(244, 63, 94, 0.9)",
                        borderWidth: 2,
                        type: "bar",
                        yAxisID: "y-axis-kpi",
                        order: 2
                    },
                    {
                        label: "Net Income ($M)",
                        data: [...netHist, null],
                        borderColor: "rgba(16, 185, 129, 0.9)",
                        backgroundColor: "transparent",
                        borderWidth: 2.5,
                        type: "line",
                        tension: 0.2,
                        yAxisID: "y-axis-kpi",
                        order: 1
                    },
                    {
                        label: "Net Income Forecast ($M)",
                        data: netForecastSeries,
                        borderColor: "rgba(244, 63, 94, 0.9)",
                        backgroundColor: "transparent",
                        borderWidth: 2,
                        borderDash: [5, 5],
                        type: "line",
                        pointStyle: "triangle",
                        pointRadius: 6,
                        yAxisID: "y-axis-kpi",
                        order: 0
                    },
                    {
                        label: "Operating Margin (%)",
                        data: [...marginHist, null],
                        borderColor: "rgba(59, 130, 246, 0.8)",
                        backgroundColor: "rgba(59, 130, 246, 0.05)",
                        borderWidth: 1.5,
                        type: "line",
                        tension: 0.1,
                        yAxisID: "y-axis-margin",
                        order: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: "top",
                        labels: {
                            color: "#9ca3af",
                            font: { family: "Inter", size: 11 }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed.y !== null) {
                                    label += context.parsed.y;
                                    // Add confidence interval details on forecasted values
                                    if (context.dataIndex === labels.length - 1 && context.datasetIndex === 1) {
                                        label += ` (95% CI: $${data.forecasts.revenue.lower_95}M - $${data.forecasts.revenue.upper_95}M)`;
                                    }
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { color: "rgba(255, 255, 255, 0.04)" },
                        ticks: { color: "#9ca3af", font: { family: "Inter" } }
                    },
                    "y-axis-kpi": {
                        type: "linear",
                        position: "left",
                        grid: { color: "rgba(255, 255, 255, 0.04)" },
                        ticks: { color: "#9ca3af", font: { family: "Inter" } },
                        title: {
                            display: true,
                            text: "KPI Valuation ($ Millions)",
                            color: "#9ca3af"
                        }
                    },
                    "y-axis-margin": {
                        type: "linear",
                        position: "right",
                        grid: { drawOnChartArea: false },
                        ticks: { color: "#9ca3af", font: { family: "Inter" } },
                        title: {
                            display: true,
                            text: "Operating Margin (%)",
                            color: "#9ca3af"
                        },
                        min: 0,
                        max: 100
                    }
                }
            }
        });
    }
});
