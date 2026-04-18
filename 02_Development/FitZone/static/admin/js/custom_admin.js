/* ============================================================
   FitZone Admin — Dark Theme JS
   Sidebar, Charts (ApexCharts), Animated Counters, Clock
   ============================================================ */

document.addEventListener('DOMContentLoaded', function () {

    /* ---- Theme Toggle (dark/light with persistence) ---- */
    const THEME_STORAGE_KEY = 'fitzone_admin_theme';
    const themeToggle = document.getElementById('theme-toggle');

    function getPreferredTheme() {
        const savedTheme = localStorage.getItem(THEME_STORAGE_KEY);
        if (savedTheme === 'dark' || savedTheme === 'light') {
            return savedTheme;
        }

        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
            return 'light';
        }

        return 'dark';
    }

    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem(THEME_STORAGE_KEY, theme);

        if (!themeToggle) return;

        const icon = themeToggle.querySelector('i');
        const label = themeToggle.querySelector('.theme-toggle-label');
        const isDark = theme === 'dark';

        themeToggle.setAttribute('aria-pressed', String(!isDark));
        themeToggle.setAttribute('title', isDark ? 'Switch to light mode' : 'Switch to dark mode');

        if (icon) {
            icon.classList.toggle('fa-sun', isDark);
            icon.classList.toggle('fa-moon', !isDark);
        }

        if (label) {
            label.textContent = isDark ? 'Light' : 'Dark';
        }
    }

    applyTheme(getPreferredTheme());

    if (themeToggle) {
        themeToggle.addEventListener('click', function () {
            const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
            const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';
            applyTheme(nextTheme);
            initDashboardCharts();
        });
    }

    /* ---- Sidebar Toggle ---- */
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const backdrop = document.getElementById('sidebar-backdrop');

    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function () {
            if (window.innerWidth > 1024) {
                sidebar.classList.toggle('collapsed');
            } else {
                sidebar.classList.toggle('active');
                if (backdrop) backdrop.classList.toggle('active');
            }
        });
    }

    // Close sidebar on backdrop click (mobile)
    if (backdrop) {
        backdrop.addEventListener('click', function () {
            sidebar.classList.remove('active');
            backdrop.classList.remove('active');
        });
    }

    // Close sidebar clicking outside (mobile)
    document.addEventListener('click', function (event) {
        if (window.innerWidth <= 1024) {
            if (sidebar && sidebarToggle && !sidebar.contains(event.target) &&
                !sidebarToggle.contains(event.target) && sidebar.classList.contains('active')) {
                sidebar.classList.remove('active');
                if (backdrop) backdrop.classList.remove('active');
            }
        }
    });

    /* ---- Sidebar Accordion (smooth height transitions) ---- */
    const groupTitles = document.querySelectorAll('.group-title');
    groupTitles.forEach(function (title) {
        title.addEventListener('click', function () {
            const group = this.parentElement;
            const items = group.querySelector('.group-items');
            const arrow = this.querySelector('.group-arrow');

            const isOpen = items.classList.contains('open');

            // Close all groups (accordion)
            document.querySelectorAll('.group-items').forEach(function (el) {
                el.style.maxHeight = null;
                el.classList.remove('open');
            });
            document.querySelectorAll('.group-arrow').forEach(function (el) {
                el.style.transform = 'rotate(0deg)';
            });
            document.querySelectorAll('.group-title').forEach(function (el) {
                el.classList.remove('active');
            });

            if (!isOpen) {
                items.classList.add('open');
                items.style.maxHeight = items.scrollHeight + 'px';
                if (arrow) arrow.style.transform = 'rotate(90deg)';
                this.classList.add('active');
            }
        });
    });

    // Auto-open group if a model inside it is active
    document.querySelectorAll('.group-items a.active').forEach(function (activeLink) {
        const group = activeLink.closest('.sidebar-group');
        if (group) {
            const items = group.querySelector('.group-items');
            const title = group.querySelector('.group-title');
            const arrow = title ? title.querySelector('.group-arrow') : null;
            items.classList.add('open');
            items.style.maxHeight = items.scrollHeight + 'px';
            if (arrow) arrow.style.transform = 'rotate(90deg)';
            if (title) title.classList.add('active');
        }
    });

    /* ---- Animated Counter (count-up) ---- */
    function animateCounter(el) {
        const target = parseInt(el.textContent.replace(/[^0-9]/g, ''), 10);
        if (isNaN(target) || target === 0) return;

        const duration = 1200;
        const startTime = performance.now();

        function step(now) {
            const elapsed = now - startTime;
            const progress = Math.min(elapsed / duration, 1);
            // Ease out cubic
            const eased = 1 - Math.pow(1 - progress, 3);
            el.textContent = Math.floor(eased * target).toLocaleString();
            if (progress < 1) requestAnimationFrame(step);
        }

        requestAnimationFrame(step);
    }

    document.querySelectorAll('.dashboard-stat-value').forEach(function (el) {
        if (el.textContent.trim() !== '---') {
            animateCounter(el);
        }
    });

    /* ---- Header Clock ---- */
    const clockEl = document.getElementById('header-clock');
    if (clockEl) {
        function updateClock() {
            const now = new Date();
            const h = String(now.getHours()).padStart(2, '0');
            const m = String(now.getMinutes()).padStart(2, '0');
            const s = String(now.getSeconds()).padStart(2, '0');
            clockEl.textContent = h + ':' + m + ':' + s;
        }
        updateClock();
        setInterval(updateClock, 1000);
    }

    /* ---- Dashboard ApexCharts (Dark Theme) ---- */
    function initDashboardCharts() {
        if (typeof ApexCharts === 'undefined') return;

        const isLight = (document.documentElement.getAttribute('data-theme') || 'dark') === 'light';
        const css = getComputedStyle(document.documentElement);
        const accent = css.getPropertyValue('--accent').trim() || '#f97316';
        const textSecondary = css.getPropertyValue('--text-secondary').trim() || '#8b8ba3';
        const chartGrid = isLight ? 'rgba(15,23,42,0.12)' : 'rgba(255,255,255,0.05)';
        const chartStroke = isLight ? '#ffffff' : '#16161f';
        const chartColors = [accent, '#8b5cf6', '#06b6d4', '#22c55e', '#eab308'];

        ['userGrowthChart', 'revenueChart', 'membershipChart', 'bookingChart'].forEach(function (id) {
            const container = document.getElementById(id);
            if (container) {
                container.innerHTML = '';
            }
        });

        const chartTheme = {
            chart: {
                foreColor: textSecondary,
                background: 'transparent',
                toolbar: { show: false }
            },
            grid: {
                borderColor: chartGrid,
                strokeDashArray: 4
            },
            tooltip: {
                theme: isLight ? 'light' : 'dark',
                style: { fontSize: '13px' },
                y: { formatter: function (val) { return val.toLocaleString(); } }
            },
            xaxis: {
                labels: { style: { colors: textSecondary, fontSize: '12px' } },
                axisBorder: { color: chartGrid },
                axisTicks: { color: chartGrid }
            },
            yaxis: {
                labels: { style: { colors: textSecondary, fontSize: '12px' } }
            }
        };

        function safeRender(selector, options) {
            try {
                const el = document.getElementById(selector);
                if (!el) return;

                const labels = JSON.parse(el.dataset.labels || '[]');
                const series = JSON.parse(el.dataset.series || '[]');

                if (series.length === 0 || (Array.isArray(series[0]) && series[0].length === 0)) {
                    el.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:260px;color:#5d5d78;font-size:0.9rem;">No data available yet</div>';
                    return;
                }

                // Merge dark theme defaults
                options.chart = Object.assign({}, chartTheme.chart, options.chart);
                options.grid = options.grid || chartTheme.grid;
                options.tooltip = options.tooltip || chartTheme.tooltip;
                options.xaxis = Object.assign({}, chartTheme.xaxis, options.xaxis || {});
                options.yaxis = options.yaxis || chartTheme.yaxis;

                // Inject data
                if (options.chart.type === 'pie' || options.chart.type === 'donut') {
                    options.series = series;
                    options.labels = labels;
                } else {
                    options.series[0].data = series;
                    options.xaxis.categories = labels;
                }

                new ApexCharts(el, options).render();
            } catch (err) {
                console.error('Chart error (' + selector + '):', err);
            }
        }

        // 1. User Growth — Bar Chart
        safeRender('userGrowthChart', {
            chart: { type: 'bar', height: 280 },
            series: [{ name: 'New Users', data: [] }],
            colors: [accent],
            plotOptions: {
                bar: {
                    borderRadius: 6,
                    columnWidth: '50%',
                    distributed: false
                }
            },
            dataLabels: { enabled: false },
            fill: {
                type: 'gradient',
                gradient: {
                    shade: 'dark',
                    type: 'vertical',
                    shadeIntensity: 0.3,
                    opacityFrom: 1,
                    opacityTo: 0.8,
                    stops: [0, 100]
                }
            }
        });

        // 2. Revenue — Area Chart
        safeRender('revenueChart', {
            chart: { type: 'area', height: 280 },
            series: [{ name: 'Revenue (Rs.)', data: [] }],
            colors: [accent],
            stroke: { curve: 'smooth', width: 2.5 },
            fill: {
                type: 'gradient',
                gradient: {
                    shadeIntensity: 1,
                    opacityFrom: 0.35,
                    opacityTo: 0.05,
                    stops: [0, 90, 100]
                }
            },
            dataLabels: { enabled: false }
        });

        // 3. Membership — Donut Chart
        safeRender('membershipChart', {
            chart: { type: 'donut', height: 300 },
            colors: chartColors,
            legend: {
                position: 'bottom',
                labels: { colors: '#8b8ba3' }
            },
            plotOptions: {
                pie: {
                    donut: {
                        size: '72%',
                        labels: {
                            show: true,
                            total: {
                                show: true,
                                label: 'Plans',
                                color: textSecondary,
                                fontSize: '14px'
                            },
                            value: {
                                color: css.getPropertyValue('--text-primary').trim() || '#eaeaf0',
                                fontSize: '22px',
                                fontWeight: 700
                            }
                        }
                    }
                }
            },
            stroke: { show: true, width: 2, colors: [chartStroke] }
        });

        // 4. Booking — Pie Chart
        safeRender('bookingChart', {
            chart: { type: 'pie', height: 300 },
            colors: chartColors,
            legend: {
                position: 'bottom',
                labels: { colors: textSecondary }
            },
            stroke: { show: true, width: 2, colors: [chartStroke] }
        });
    }

    initDashboardCharts();

    /* ---- Stagger animations for app cards ---- */
    document.querySelectorAll('.app-card').forEach(function (card, i) {
        card.style.animationDelay = (0.05 + i * 0.06) + 's';
    });

    document.querySelectorAll('.chart-card').forEach(function (card, i) {
        card.style.animationDelay = (0.08 + i * 0.08) + 's';
    });
});
