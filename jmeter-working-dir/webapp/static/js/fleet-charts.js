/* Fleet Charts — Lightweight canvas time-series for fleet monitoring */

const CHART_COLORS = [
    '#3b82f6', '#22c55e', '#f59e0b', '#ef4444',
    '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'
];

class FleetChart {
    constructor(canvas, options) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.opts = Object.assign({
            title: '',
            yMin: 0,
            yMax: null,       // null = auto-scale
            yLabel: '%',
            yFixed: 0,        // decimal places
            windowMs: 5 * 60 * 1000, // 5 min rolling window
            gridLines: 4,
            showLegend: true,
        }, options);
        this.series = {};     // { seriesId: { label, colorIdx, points: [{t, v}] } }
        this.hoverX = null;
        this.hoverY = null;
        this._raf = null;
        this._dirty = true;
        this._boundMouseMove = this._onMouseMove.bind(this);
        this._boundMouseLeave = this._onMouseLeave.bind(this);
        this._setupInteraction();
        this._startLoop();
    }

    addSeries(id, label) {
        if (this.series[id]) return;
        const idx = Object.keys(this.series).length % CHART_COLORS.length;
        this.series[id] = { label: label, colorIdx: idx, points: [] };
    }

    addPoint(seriesId, timestamp, value) {
        if (!this.series[seriesId]) return;
        this.series[seriesId].points.push({ t: timestamp, v: value });
        this._trimPoints(seriesId);
        this._dirty = true;
    }

    _trimPoints(seriesId) {
        var pts = this.series[seriesId].points;
        var cutoff = Date.now() - this.opts.windowMs - 30000; // 30s grace
        while (pts.length > 0 && pts[0].t < cutoff) pts.shift();
    }

    _onMouseMove(e) {
        var rect = this.canvas.getBoundingClientRect();
        this.hoverX = e.clientX - rect.left;
        this.hoverY = e.clientY - rect.top;
        this._dirty = true;
    }

    _onMouseLeave() {
        this.hoverX = null;
        this.hoverY = null;
        this._dirty = true;
    }

    _setupInteraction() {
        this.canvas.addEventListener('mousemove', this._boundMouseMove);
        this.canvas.addEventListener('mouseleave', this._boundMouseLeave);
    }

    _startLoop() {
        var self = this;
        var loop = function() {
            if (self._dirty) {
                self._render();
                self._dirty = false;
            }
            self._raf = requestAnimationFrame(loop);
        };
        this._raf = requestAnimationFrame(loop);
    }

    _getYBounds() {
        if (this.opts.yMax != null) return { min: this.opts.yMin, max: this.opts.yMax };
        var max = 10;
        for (var key in this.series) {
            var s = this.series[key];
            for (var i = 0; i < s.points.length; i++) {
                if (s.points[i].v > max) max = s.points[i].v;
            }
        }
        // Round up to nice number
        max = Math.ceil(max * 1.15);
        if (max <= 100 && this.opts.yLabel === '%') max = 100;
        return { min: this.opts.yMin, max: max };
    }

    _render() {
        var c = this.canvas;
        var ctx = this.ctx;
        var dpr = window.devicePixelRatio || 1;
        var w = c.clientWidth;
        var h = c.clientHeight;

        // Guard: if canvas has no size (hidden/detached), skip render
        if (w === 0 || h === 0) return;

        c.width = w * dpr;
        c.height = h * dpr;
        ctx.scale(dpr, dpr);

        // Colors from CSS vars or fallback
        var style = getComputedStyle(document.documentElement);
        var textColor = style.getPropertyValue('--color-text-secondary').trim() || '#94a3b8';
        var gridColor = style.getPropertyValue('--color-border').trim() || '#e2e8f0';
        var bgColor = style.getPropertyValue('--color-surface').trim() || '#ffffff';

        // Layout
        var pad = { top: 24, right: 12, bottom: 28, left: 44 };
        var plotW = w - pad.left - pad.right;
        var plotH = h - pad.top - pad.bottom;

        // Guard: if plot area is too small, skip
        if (plotW < 10 || plotH < 10) return;

        // Clear
        ctx.fillStyle = bgColor;
        ctx.fillRect(0, 0, w, h);

        // Title
        ctx.fillStyle = textColor;
        ctx.font = '600 11px system-ui, sans-serif';
        ctx.textAlign = 'left';
        ctx.fillText(this.opts.title, pad.left, 14);

        // Y axis
        var yBounds = this._getYBounds();
        var yRange = yBounds.max - yBounds.min;
        if (yRange === 0) yRange = 1; // prevent division by zero
        ctx.font = '10px system-ui, sans-serif';
        ctx.textAlign = 'right';
        ctx.strokeStyle = gridColor;
        ctx.lineWidth = 0.5;
        for (var i = 0; i <= this.opts.gridLines; i++) {
            var frac = i / this.opts.gridLines;
            var y = pad.top + plotH - frac * plotH;
            var val = yBounds.min + frac * yRange;
            // Grid line
            ctx.beginPath();
            ctx.moveTo(pad.left, y);
            ctx.lineTo(pad.left + plotW, y);
            ctx.stroke();
            // Label
            ctx.fillStyle = textColor;
            ctx.fillText(val.toFixed(this.opts.yFixed) + (i === this.opts.gridLines ? this.opts.yLabel : ''), pad.left - 4, y + 3);
        }

        // Time bounds
        var now = Date.now();
        var tMin = now - this.opts.windowMs;
        var tMax = now;
        var tRange = tMax - tMin;
        if (tRange === 0) tRange = 1; // prevent division by zero

        // Time axis labels (MM:SS)
        ctx.textAlign = 'center';
        ctx.fillStyle = textColor;
        var timeSteps = 5;
        for (var ti = 0; ti <= timeSteps; ti++) {
            var tFrac = ti / timeSteps;
            var tx = pad.left + tFrac * plotW;
            var t = tMin + tFrac * tRange;
            var d = new Date(t);
            var lbl = d.getMinutes().toString().padStart(2, '0') + ':' + d.getSeconds().toString().padStart(2, '0');
            ctx.fillText(lbl, tx, h - 6);
        }

        // Coordinate conversion helpers
        var toX = function(t) { return pad.left + ((t - tMin) / tRange) * plotW; };
        var toY = function(v) { return pad.top + plotH - ((v - yBounds.min) / yRange) * plotH; };

        // Plot each series
        var seriesIds = Object.keys(this.series);
        for (var si = 0; si < seriesIds.length; si++) {
            var id = seriesIds[si];
            var s = this.series[id];
            var pts = s.points.filter(function(p) { return p.t >= tMin; });
            if (pts.length === 0) continue;

            ctx.strokeStyle = CHART_COLORS[s.colorIdx];
            ctx.lineWidth = 1.8;
            ctx.lineJoin = 'round';
            ctx.lineCap = 'round';

            if (pts.length === 1) {
                // Single point: draw a dot
                ctx.fillStyle = CHART_COLORS[s.colorIdx];
                ctx.beginPath();
                ctx.arc(toX(pts[0].t), toY(pts[0].v), 3, 0, Math.PI * 2);
                ctx.fill();
            } else {
                ctx.beginPath();
                ctx.moveTo(toX(pts[0].t), toY(pts[0].v));
                for (var pi = 1; pi < pts.length; pi++) {
                    ctx.lineTo(toX(pts[pi].t), toY(pts[pi].v));
                }
                ctx.stroke();
            }
        }

        // Hover crosshair + tooltip
        if (this.hoverX != null && this.hoverX >= pad.left && this.hoverX <= pad.left + plotW) {
            // Vertical crosshair
            ctx.strokeStyle = textColor;
            ctx.lineWidth = 0.5;
            ctx.setLineDash([3, 3]);
            ctx.beginPath();
            ctx.moveTo(this.hoverX, pad.top);
            ctx.lineTo(this.hoverX, pad.top + plotH);
            ctx.stroke();
            ctx.setLineDash([]);

            // Find closest time
            var hoverT = tMin + ((this.hoverX - pad.left) / plotW) * tRange;

            // Tooltip
            var tooltipLines = [];
            var hoverDate = new Date(hoverT);
            tooltipLines.push(hoverDate.getHours().toString().padStart(2, '0') + ':' +
                hoverDate.getMinutes().toString().padStart(2, '0') + ':' +
                hoverDate.getSeconds().toString().padStart(2, '0'));

            for (var hi = 0; hi < seriesIds.length; hi++) {
                var hid = seriesIds[hi];
                var hs = this.series[hid];
                var hpts = hs.points;
                var closest = null, minDist = Infinity;
                for (var hpi = 0; hpi < hpts.length; hpi++) {
                    var dist = Math.abs(hpts[hpi].t - hoverT);
                    if (dist < minDist) { minDist = dist; closest = hpts[hpi]; }
                }
                if (closest && minDist < 30000) {
                    tooltipLines.push(hs.label + ': ' + closest.v.toFixed(this.opts.yFixed) + this.opts.yLabel);
                    // Draw dot at closest point
                    ctx.fillStyle = CHART_COLORS[hs.colorIdx];
                    ctx.beginPath();
                    ctx.arc(toX(closest.t), toY(closest.v), 3, 0, Math.PI * 2);
                    ctx.fill();
                }
            }

            if (tooltipLines.length > 1) {
                this._drawTooltip(ctx, this.hoverX, this.hoverY, tooltipLines, textColor, bgColor, w, h);
            }
        }

        // Legend
        if (this.opts.showLegend && seriesIds.length > 1) {
            ctx.font = '10px system-ui, sans-serif';
            ctx.textAlign = 'left';
            var lx = pad.left + plotW - seriesIds.length * 80;
            if (lx < pad.left) lx = pad.left; // prevent legend going off-left
            for (var li = 0; li < seriesIds.length; li++) {
                var ls = this.series[seriesIds[li]];
                ctx.fillStyle = CHART_COLORS[ls.colorIdx];
                ctx.fillRect(lx, 6, 8, 8);
                ctx.fillStyle = textColor;
                ctx.fillText(ls.label, lx + 11, 14);
                lx += Math.max(ctx.measureText(ls.label).width + 20, 60);
            }
        }
    }

    _drawTooltip(ctx, mx, my, lines, textColor, bgColor, canvasW, canvasH) {
        ctx.font = '10px system-ui, sans-serif';
        var lineH = 14;
        var padX = 8, padY = 6;
        var maxW = 0;
        for (var i = 0; i < lines.length; i++) {
            var lw = ctx.measureText(lines[i]).width;
            if (lw > maxW) maxW = lw;
        }
        var tipW = maxW + padX * 2;
        var tipH = lines.length * lineH + padY * 2;
        var tx = mx + 10;
        var ty = my - tipH / 2;

        // Prevent tooltip from going off-canvas
        if (tx + tipW > canvasW) tx = mx - tipW - 10;
        if (tx < 0) tx = 0;
        if (ty < 0) ty = 0;
        if (ty + tipH > canvasH) ty = canvasH - tipH;

        ctx.fillStyle = bgColor;
        ctx.strokeStyle = textColor;
        ctx.lineWidth = 0.5;
        ctx.beginPath();
        ctx.roundRect(tx, ty, tipW, tipH, 4);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = textColor;
        ctx.textAlign = 'left';
        for (var i = 0; i < lines.length; i++) {
            ctx.font = i === 0 ? 'bold 10px system-ui, sans-serif' : '10px system-ui, sans-serif';
            ctx.fillText(lines[i], tx + padX, ty + padY + (i + 1) * lineH - 3);
        }
    }

    resize() {
        this._dirty = true;
    }

    destroy() {
        if (this._raf) cancelAnimationFrame(this._raf);
        this._raf = null;
        this.canvas.removeEventListener('mousemove', this._boundMouseMove);
        this.canvas.removeEventListener('mouseleave', this._boundMouseLeave);
    }
}

// ===== Dashboard Manager =====
// Manages the 4 fleet-wide charts + per-slave drill-down charts

var FleetDashboard = {
    charts: {},          // { cpu: FleetChart, ram: FleetChart, net: FleetChart, jvm: FleetChart }
    drillCharts: {},     // { 'ip_cpu': FleetChart, 'ip_ram': FleetChart, ... }
    expandedDrill: null, // IP of expanded drill-down, or null
    _resizeHandler: null,

    init: function() {
        var cpuCanvas = document.getElementById('dashCpuChart');
        var ramCanvas = document.getElementById('dashRamChart');
        var netCanvas = document.getElementById('dashNetChart');
        var jvmCanvas = document.getElementById('dashJvmChart');
        if (!cpuCanvas) return;

        this.charts.cpu = new FleetChart(cpuCanvas, {
            title: 'CPU Usage', yMax: 100, yLabel: '%', yFixed: 0
        });
        this.charts.ram = new FleetChart(ramCanvas, {
            title: 'RAM Usage', yMax: 100, yLabel: '%', yFixed: 0
        });
        this.charts.net = new FleetChart(netCanvas, {
            title: 'Network Throughput', yMax: null, yLabel: ' KB/s', yFixed: 0
        });
        this.charts.jvm = new FleetChart(jvmCanvas, {
            title: 'JVM RSS Memory', yMax: null, yLabel: ' MB', yFixed: 0
        });

        // Ensure series exist for all slaves
        if (typeof Fleet !== 'undefined' && Fleet.slaveData) {
            var self2 = this;
            Fleet.slaveData.forEach(function(s) { self2._ensureSeries(s.ip); });
        }

        // Resize handler
        var self = this;
        this._resizeHandler = function() {
            for (var key in self.charts) {
                self.charts[key].resize();
            }
            for (var dKey in self.drillCharts) {
                self.drillCharts[dKey].resize();
            }
        };
        window.addEventListener('resize', this._resizeHandler);
    },

    _ensureSeries: function(ip) {
        var label = _slaveLabel(ip);
        for (var key in this.charts) {
            this.charts[key].addSeries(ip, label);
        }
    },

    pushMetrics: function(ip, data) {
        this._ensureSeries(ip);
        var now = Date.now();
        if (data.cpu_percent != null)
            this.charts.cpu.addPoint(ip, now, data.cpu_percent);
        if (data.ram_percent != null)
            this.charts.ram.addPoint(ip, now, data.ram_percent);
        if (data.jvm_rss_mb != null)
            this.charts.jvm.addPoint(ip, now, data.jvm_rss_mb);

        // Network throughput (delta from previous sample)
        var netRx = data.net_rx_bytes;
        var netTx = data.net_tx_bytes;
        if (netRx != null && netTx != null) {
            if (!Fleet._prevNetBytes) Fleet._prevNetBytes = {};
            var prev = Fleet._prevNetBytes[ip];
            if (prev) {
                var dtSec = (now - prev.ts) / 1000;
                if (dtSec > 0) {
                    var rxKBs = Math.max(0, (netRx - prev.rx) / 1024 / dtSec);
                    var txKBs = Math.max(0, (netTx - prev.tx) / 1024 / dtSec);
                    var combinedKBs = rxKBs + txKBs;
                    this.charts.net.addPoint(ip, now, combinedKBs);
                    // Store computed throughput for display in drill-down and averages
                    Fleet._prevNetBytes[ip] = { rx: netRx, tx: netTx, ts: now, kbps: combinedKBs };
                } else {
                    Fleet._prevNetBytes[ip] = { rx: netRx, tx: netTx, ts: now, kbps: (prev.kbps || 0) };
                }
            } else {
                Fleet._prevNetBytes[ip] = { rx: netRx, tx: netTx, ts: now };
            }
        }

        // Update drill-down if expanded for this IP
        if (this.expandedDrill === ip) {
            this._pushDrillMetrics(ip, data, now);
        }
    },

    _pushDrillMetrics: function(ip, data, now) {
        var prefix = ip + '_';
        if (this.drillCharts[prefix + 'cpu'] && data.cpu_percent != null)
            this.drillCharts[prefix + 'cpu'].addPoint(ip, now, data.cpu_percent);
        if (this.drillCharts[prefix + 'ram'] && data.ram_percent != null)
            this.drillCharts[prefix + 'ram'].addPoint(ip, now, data.ram_percent);
    },

    initDrillDown: function(ip) {
        // Destroy previous drill-down charts
        this.destroyDrillDown();
        this.expandedDrill = ip;

        var cpuCanvas = document.getElementById('drillCpuChart_' + CSS.escape(ip));
        var ramCanvas = document.getElementById('drillRamChart_' + CSS.escape(ip));
        if (!cpuCanvas || !ramCanvas) return;

        var label = _slaveLabel(ip);
        this.drillCharts[ip + '_cpu'] = new FleetChart(cpuCanvas, {
            title: 'CPU \u2014 ' + label, yMax: 100, yLabel: '%', showLegend: false
        });
        this.drillCharts[ip + '_ram'] = new FleetChart(ramCanvas, {
            title: 'RAM \u2014 ' + label, yMax: 100, yLabel: '%', showLegend: false
        });
        this.drillCharts[ip + '_cpu'].addSeries(ip, label);
        this.drillCharts[ip + '_ram'].addSeries(ip, label);

        // Backfill from fleet-wide chart data
        if (this.charts.cpu && this.charts.cpu.series[ip]) {
            var cpuPts = this.charts.cpu.series[ip].points;
            for (var i = 0; i < cpuPts.length; i++) {
                this.drillCharts[ip + '_cpu'].addPoint(ip, cpuPts[i].t, cpuPts[i].v);
            }
        }
        if (this.charts.ram && this.charts.ram.series[ip]) {
            var ramPts = this.charts.ram.series[ip].points;
            for (var i = 0; i < ramPts.length; i++) {
                this.drillCharts[ip + '_ram'].addPoint(ip, ramPts[i].t, ramPts[i].v);
            }
        }
    },

    destroyDrillDown: function() {
        for (var key in this.drillCharts) {
            this.drillCharts[key].destroy();
        }
        this.drillCharts = {};
        this.expandedDrill = null;
    },

    show: function() {
        var el = document.getElementById('fleetDashboard');
        if (el) el.style.display = '';
        if (!this.charts.cpu) this.init();
    },

    hide: function() {
        var el = document.getElementById('fleetDashboard');
        if (el) el.style.display = 'none';
    },

    destroy: function() {
        for (var key in this.charts) {
            this.charts[key].destroy();
        }
        this.charts = {};
        this.destroyDrillDown();
        if (this._resizeHandler) {
            window.removeEventListener('resize', this._resizeHandler);
            this._resizeHandler = null;
        }
    }
};

function _slaveLabel(ip) {
    if (typeof Fleet === 'undefined' || !Fleet.slaveData) return ip;
    var s = Fleet.slaveData.find(function(sl) { return sl.ip === ip; });
    return s && s.nickname ? s.nickname : ip;
}
