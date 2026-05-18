# -*- coding: utf-8 -*-
"""
Generate Weekly Report Đối Soát Tồn Kho KFM vs ABA
====================================================
Aggregates daily reconciliation data for the PREVIOUS WEEK
and produces an HTML report with:
  1. Weekly summary table (T2→CN)
  2. Statistics table by category (Đông/Mát/TCNK)
  3. Trend charts for accuracy rate (Item/SKU/KG) — 7 days
  4. Pie chart of KG & Item proportion by category
  5. Auto-generated commentary
  6. Consolidated discrepancy detail table for the full week
"""

import os
import sys
import io
import json
import math
import argparse
from datetime import datetime, timedelta
from collections import defaultdict

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import base64

# Import shared functions from daily report
from generate import (
    load_master_data,
    load_weight_data,
    load_doi_soat_files,
    compute_stats,
    acc_precise,
    generate_combo_chart_image,
    generate_pie_chart_image,
    OUTPUT_DIR,
)

# sys.stdout encoding is already set via generate_report import
try:
    sys.stdout.reconfigure(encoding='utf-8')
except (AttributeError, OSError):
    pass


def generate_stacked_chart_image(dates, data_by_cat, colors_by_cat, labels_by_cat, y_label):
    """Generate a stacked bar chart as base64 PNG for fallback display.
    data_by_cat: dict of cat_key -> list of values per date
    """
    fig, ax = plt.subplots(figsize=(10, 4.2))
    fig.patch.set_facecolor('#1e293b')
    ax.set_facecolor('#1e293b')

    x = np.arange(len(dates))
    width = 0.5
    cat_keys = list(data_by_cat.keys())

    bottom = np.zeros(len(dates))
    for cat_key in cat_keys:
        values = data_by_cat[cat_key]
        color = colors_by_cat[cat_key]
        label = labels_by_cat[cat_key]
        ax.bar(x, values, width, label=label, bottom=bottom,
               color=color + '99', edgecolor=color, linewidth=0.8)
        bottom += np.array(values)

    ax.set_ylabel(y_label, color='#64748b', fontsize=10, fontweight='600')
    ax.set_xticks(x)
    ax.set_xticklabels(dates, color='#94a3b8', fontsize=9)
    ax.tick_params(axis='y', colors='#94a3b8', labelsize=9)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v:,.0f}'))
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#ffffff10')
    ax.spines['bottom'].set_color('#ffffff10')
    ax.grid(axis='y', color='#ffffff0a', linewidth=0.5)

    leg = ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.12), ncol=len(cat_keys),
                    facecolor='#1e293b', edgecolor='none', labelcolor='#94a3b8', fontsize=9)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                facecolor='#1e293b', edgecolor='none', pad_inches=0.3)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def get_week_range(iso_year, iso_week):
    """Return (monday, sunday) datetime for the given ISO year/week."""
    # Jan 4 is always in ISO week 1
    jan4 = datetime(iso_year, 1, 4)
    # Monday of week 1
    week1_monday = jan4 - timedelta(days=jan4.isoweekday() - 1)
    # Monday of target week
    monday = week1_monday + timedelta(weeks=iso_week - 1)
    sunday = monday + timedelta(days=6)
    return monday, sunday


def get_previous_week_info(ref_date=None):
    """Get ISO year and week number for the previous week."""
    if ref_date is None:
        ref_date = datetime.now()
    # Go back 7 days to land in the previous week
    prev_week_date = ref_date - timedelta(days=7)
    iso_year, iso_week, _ = prev_week_date.isocalendar()
    return iso_year, iso_week


# ─────────────────────────────────────────────
# Auto Comment Generator
# ─────────────────────────────────────────────
def generate_auto_comment(weekly_rows, acc_averages, prev_acc_averages,
                          week_label, prev_week_label,
                          weekly_detail_items_all):
    """
    Generate auto commentary for the weekly report.
    acc_averages: dict with keys 'item', 'sku', 'kg'
    prev_acc_averages: dict with keys 'item', 'sku', 'kg' (values can be None)
    Returns HTML string.
    """
    # Calculate this week's stats
    data_rows = [r for r in weekly_rows if r['has_data']]
    if not data_rows:
        return '<p style="color: var(--text-muted);">Không có dữ liệu để nhận xét.</p>'

    avg_acc = acc_averages['item']  # used for best/worst day

    # Best / worst day
    best_row = max(data_rows, key=lambda r: r['acc'])
    worst_row = min(data_rows, key=lambda r: r['acc'])

    # Lệch dương / âm totals
    total_lech_duong = sum(r['lech_duong'] for r in data_rows)
    total_lech_am = sum(r['lech_am'] for r in data_rows)
    total_lech = total_lech_duong + total_lech_am

    pct_duong = round(total_lech_duong / total_lech * 100, 1) if total_lech > 0 else 0
    pct_am = round(total_lech_am / total_lech * 100, 1) if total_lech > 0 else 0

    # Recurring discrepancy items (appear ≥ 3 days)
    barcode_freq = defaultdict(int)
    for items_list in weekly_detail_items_all.values():
        seen = set()
        for it in items_list:
            if it['barcode'] not in seen:
                barcode_freq[it['barcode']] += 1
                seen.add(it['barcode'])
    recurring = {bc: freq for bc, freq in barcode_freq.items() if freq >= 3}
    n_recurring = len(recurring)

    # ── Helper for trend text ──
    def _trend_span(cur, prev):
        if prev is None:
            return ''
        diff = round(cur - prev, 2)
        if diff > 0:
            return f' (<span style="color: var(--accent-green);">+{diff:.2f}%</span> vs {prev_week_label})'
        elif diff < 0:
            return f' (<span style="color: var(--accent-red);">{diff:.2f}%</span> vs {prev_week_label})'
        return f' (<span style="color: var(--text-muted);">không đổi</span> vs {prev_week_label})'

    comments = []

    # 1. Average accuracy — Item / SKU / KG
    item_trend = _trend_span(acc_averages['item'], prev_acc_averages['item'])
    sku_trend = _trend_span(acc_averages['sku'], prev_acc_averages['sku'])
    kg_trend = _trend_span(acc_averages['kg'], prev_acc_averages['kg'])

    comments.append(
        f'Tỷ lệ chính xác trung bình tuần:'
        f'<div style="margin: 0.4rem 0 0 1rem; line-height: 2;">'
        f'• <strong>Item: {acc_averages["item"]:.2f}%</strong>{item_trend}<br>'
        f'• <strong>SKU: {acc_averages["sku"]:.2f}%</strong>{sku_trend}<br>'
        f'• <strong>KG: {acc_averages["kg"]:.2f}%</strong>{kg_trend}'
        f'</div>'
    )

    # 2. Best / worst day
    comments.append(
        f'Ngày tốt nhất: <strong>{best_row["thu"]} ({best_row["ngay"]})</strong> — '
        f'<span style="color: var(--accent-green);">{best_row["acc"]:.2f}%</span> · '
        f'Ngày cần cải thiện: <strong>{worst_row["thu"]} ({worst_row["ngay"]})</strong> — '
        f'<span style="color: var(--accent-red);">{worst_row["acc"]:.2f}%</span>'
    )

    # 3. Lệch proportion
    comments.append(
        f'Lệch dương chiếm <strong>{pct_duong}%</strong>, '
        f'lệch âm chiếm <strong>{pct_am}%</strong> tổng lệch '
        f'(tổng: <strong>{total_lech:,}</strong> items)'
    )

    # 4. Recurring items
    if n_recurring > 0:
        comments.append(
            f'Có <strong style="color: var(--accent-red);">{n_recurring}</strong> mã lệch '
            f'xuất hiện ≥ 3 ngày trong tuần — cần ưu tiên kiểm tra'
        )
    else:
        comments.append(
            'Không có mã lệch nào xuất hiện ≥ 3 ngày — tình hình ổn định'
        )

    # 5. Days with acc < 99.5%
    bad_days = [r for r in data_rows if r['acc'] < 99.5]
    if bad_days:
        bad_list = ', '.join(f'{r["thu"]} ({r["acc"]:.2f}%)' for r in bad_days)
        comments.append(
            f'<span style="color: var(--accent-red);">⚠️</span> '
            f'Có <strong>{len(bad_days)}</strong> ngày tỷ lệ chính xác dưới 99.5%: {bad_list}'
        )
    else:
        comments.append(
            '<span style="color: var(--accent-green);">✅</span> '
            'Tất cả các ngày trong tuần đều đạt tỷ lệ chính xác ≥ 99.5%'
        )

    # Build HTML
    items_html = '\n'.join(
        f'<li style="margin-bottom: 0.6rem; line-height: 1.6;">{c}</li>'
        for c in comments
    )

    return f'''
    <ul style="list-style: none; padding: 0; margin: 0;">
        {items_html}
    </ul>
    '''


# ─────────────────────────────────────────────
# Generate Weekly HTML Report
# ─────────────────────────────────────────────
def generate_weekly_html(daily_stats, all_days, target_iso_year, target_iso_week,
                         category_map, weight_map):
    """Generate the weekly HTML report for the specified ISO week."""

    week_monday, week_sunday = get_week_range(target_iso_year, target_iso_week)
    week_label = f'W{target_iso_week}'
    week_full_label = f'W{target_iso_week}-{target_iso_year}'

    # Previous week for comparison
    prev_iso_year, prev_iso_week = target_iso_year, target_iso_week - 1
    if prev_iso_week < 1:
        prev_iso_year -= 1
        prev_iso_week = datetime(prev_iso_year, 12, 28).isocalendar()[1]
    prev_week_label = f'W{prev_iso_week}'
    prev_week_full_label = f'W{prev_iso_week}-{prev_iso_year}'
    prev_monday, prev_sunday = get_week_range(prev_iso_year, prev_iso_week)

    # Map daily_stats by date for quick lookup
    stats_by_date = {ds['date'].strftime('%Y-%m-%d'): ds for ds in daily_stats}

    # Map all_days by date for detail items
    days_by_date = {d['date'].strftime('%Y-%m-%d'): d for d in all_days}

    cats = ['ĐÔNG', 'MÁT', 'TCNK']
    cat_labels = {'ĐÔNG': 'Hàng Đông', 'MÁT': 'Hàng Mát', 'TCNK': 'TCNK'}
    cat_colors = {'ĐÔNG': '#60a5fa', 'MÁT': '#34d399', 'TCNK': '#fbbf24'}

    thu_labels = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN']

    # ── Build weekly rows for target week ──
    week_days = [week_monday + timedelta(days=i) for i in range(7)]
    weekly_rows = []
    weekly_acc_values = []
    weekly_detail_items_all = {}  # date_key -> [items with discrepancy]

    for i, wd in enumerate(week_days):
        key = wd.strftime('%Y-%m-%d')
        ds = stats_by_date.get(key)
        if ds:
            day_acc = acc_precise(ds['totals']['item_lech'], ds['totals']['item_KFM'])
            weekly_acc_values.append(day_acc)
            weekly_rows.append({
                'thu': thu_labels[i],
                'ngay': wd.strftime('%d/%m/%Y'),
                'acc': day_acc,
                'lech_duong': ds['totals']['lech_duong'],
                'lech_am': ds['totals']['lech_am'],
                'tong_lech': ds['totals']['tong_lech'],
                'ton_kdb': ds['totals']['item_KFM'],
                'has_data': True,
            })
            # Collect discrepancy items
            day_data = days_by_date.get(key)
            if day_data:
                discrepant = [it for it in day_data['items']
                              if it['ton_KFM'] != it['ton_ABA']]
                if discrepant:
                    weekly_detail_items_all[key] = discrepant
        else:
            weekly_rows.append({
                'thu': thu_labels[i],
                'ngay': wd.strftime('%d/%m/%Y'),
                'acc': None, 'lech_duong': 0, 'lech_am': 0,
                'tong_lech': 0, 'ton_kdb': 0, 'has_data': False,
            })

    avg_acc = sum(weekly_acc_values) / len(weekly_acc_values) if weekly_acc_values else 0
    avg_acc = math.floor(avg_acc * 100) / 100

    # ── Build previous week rows for comparison ──
    prev_week_days = [prev_monday + timedelta(days=i) for i in range(7)]
    prev_weekly_acc_values = []
    for wd in prev_week_days:
        key = wd.strftime('%Y-%m-%d')
        ds = stats_by_date.get(key)
        if ds:
            day_acc = acc_precise(ds['totals']['item_lech'], ds['totals']['item_KFM'])
            prev_weekly_acc_values.append(day_acc)
    prev_avg_acc = (sum(prev_weekly_acc_values) / len(prev_weekly_acc_values)
                    if prev_weekly_acc_values else None)
    if prev_avg_acc is not None:
        prev_avg_acc = math.floor(prev_avg_acc * 100) / 100

    # ── Summary data (use last day of week with data) ──
    last_day_stats = None
    for wd in reversed(week_days):
        key = wd.strftime('%Y-%m-%d')
        if key in stats_by_date:
            last_day_stats = stats_by_date[key]
            break

    if not last_day_stats:
        print("   ❌ Không có dữ liệu trong tuần này!")
        return None

    # Summary values
    total_kfm_sku = sum(last_day_stats['categories'][c]['sku'] for c in cats)
    total_kfm_item = sum(last_day_stats['categories'][c]['item_KFM'] for c in cats)
    total_aba_item = sum(last_day_stats['categories'][c]['item_ABA'] for c in cats)
    total_kfm_kg = sum(last_day_stats['categories'][c]['kg_KFM'] for c in cats)
    total_aba_kg = sum(last_day_stats['categories'][c]['kg_ABA'] for c in cats)

    # ── Stats table by category (last day of week) ──
    table_rows = []
    for cat in cats:
        cs = last_day_stats['categories'][cat]
        table_rows.append({
            'cat': cat_labels[cat],
            'color': cat_colors[cat],
            'sku': cs['sku'],
            'item_KFM': cs['item_KFM'],
            'item_ABA': cs['item_ABA'],
            'kg_KFM': cs['kg_KFM'],
            'kg_ABA': cs['kg_ABA'],
        })

    # ── Trend data for THIS WEEK (7 days) ──
    trend_dates = []
    trend_item_kfm = []
    trend_item_aba = []
    trend_item_acc = []
    trend_sku_kfm = []
    trend_sku_aba = []
    trend_sku_acc = []
    trend_kg_kfm = []
    trend_kg_aba = []
    trend_kg_acc = []

    # Per-category trend data
    trend_cat_item = {'ĐÔNG': [], 'MÁT': [], 'TCNK': []}
    trend_cat_kg = {'ĐÔNG': [], 'MÁT': [], 'TCNK': []}

    for wd in week_days:
        key = wd.strftime('%Y-%m-%d')
        ds = stats_by_date.get(key)
        if ds:
            trend_dates.append(ds['date_str'])
            t_item_kfm = sum(ds['categories'][c]['item_KFM'] for c in cats)
            t_item_lech = sum(ds['categories'][c]['item_lech'] for c in cats)
            t_sku_total = sum(ds['categories'][c]['sku'] for c in cats)
            t_sku_lech = sum(ds['categories'][c]['sku_lech'] for c in cats)
            t_kg_kfm = sum(ds['categories'][c]['kg_KFM'] for c in cats)
            t_kg_lech = sum(ds['categories'][c]['kg_lech'] for c in cats)

            item_acc = acc_precise(t_item_lech, t_item_kfm)
            sku_acc = acc_precise(t_sku_lech, t_sku_total)
            kg_acc = acc_precise(t_kg_lech, t_kg_kfm)

            trend_item_kfm.append(t_item_kfm)
            trend_item_aba.append(t_item_kfm - t_item_lech)
            trend_item_acc.append(item_acc)

            trend_sku_kfm.append(t_sku_total)
            trend_sku_aba.append(t_sku_total - t_sku_lech)
            trend_sku_acc.append(sku_acc)

            trend_kg_kfm.append(round(t_kg_kfm, 2))
            trend_kg_aba.append(round(t_kg_kfm - t_kg_lech, 2))
            trend_kg_acc.append(kg_acc)

            # Per-category
            for cat in cats:
                trend_cat_item[cat].append(ds['categories'][cat]['item_KFM'])
                trend_cat_kg[cat].append(round(ds['categories'][cat]['kg_KFM'], 2))

    if not trend_dates:
        print("   ❌ Không có trend data cho tuần này!")
        return None

    # ── Previous week averages for comparison ──
    prev_item_acc_values = []
    prev_sku_acc_values = []
    prev_kg_acc_values = []
    prev_total_items = []
    prev_total_kgs = []
    for wd in prev_week_days:
        key = wd.strftime('%Y-%m-%d')
        ds = stats_by_date.get(key)
        if ds:
            t_item_kfm = sum(ds['categories'][c]['item_KFM'] for c in cats)
            t_item_lech = sum(ds['categories'][c]['item_lech'] for c in cats)
            t_sku_total = sum(ds['categories'][c]['sku'] for c in cats)
            t_sku_lech = sum(ds['categories'][c]['sku_lech'] for c in cats)
            t_kg_kfm = sum(ds['categories'][c]['kg_KFM'] for c in cats)
            t_kg_lech = sum(ds['categories'][c]['kg_lech'] for c in cats)
            prev_item_acc_values.append(acc_precise(t_item_lech, t_item_kfm))
            prev_sku_acc_values.append(acc_precise(t_sku_lech, t_sku_total))
            prev_kg_acc_values.append(acc_precise(t_kg_lech, t_kg_kfm))
            prev_total_items.append(t_item_kfm)
            prev_total_kgs.append(t_kg_kfm)

    # ── Insight builders ──
    def _fmt_change_acc(current, previous):
        if previous is None:
            return None, None, None
        diff = round(current - previous, 2)
        return diff, current, previous

    def _fmt_change_qty(current, previous):
        if previous is None or previous == 0:
            return None, None, None
        pct = round((current - previous) / previous * 100, 2)
        return pct, current, previous

    def _build_insight_html(label, diff, current, previous, is_acc=True):
        if diff is None:
            return f'''<div class="insight-badge">
                <div class="insight-label">{label}</div>
                <div class="insight-value" style="color: var(--text-muted);">N/A</div>
            </div>'''
        if is_acc:
            if diff > 0:
                arrow, color, sign = '▲', 'var(--accent-green)', '+'
            elif diff < 0:
                arrow, color, sign = '▼', 'var(--accent-red)', ''
            else:
                arrow, color, sign = '—', 'var(--text-muted)', ''
            return f'''<div class="insight-badge">
                <div class="insight-label">{label}</div>
                <div class="insight-value" style="color: {color};">{arrow} {sign}{diff:.2f}%</div>
                <div class="insight-detail">{previous:.2f}% → {current:.2f}%</div>
            </div>'''
        else:
            if diff > 0:
                arrow, color, sign = '▲', 'var(--accent-green)', '+'
            elif diff < 0:
                arrow, color, sign = '▼', 'var(--accent-red)', ''
            else:
                arrow, color, sign = '—', 'var(--text-muted)', ''
            if isinstance(current, float):
                cur_str, prev_str = f'{current:,.2f}', f'{previous:,.2f}'
            else:
                cur_str, prev_str = f'{current:,}', f'{previous:,}'
            return f'''<div class="insight-badge">
                <div class="insight-label">{label}</div>
                <div class="insight-value" style="color: {color};">{arrow} {sign}{diff:.2f}%</div>
                <div class="insight-detail">{prev_str} → {cur_str}</div>
            </div>'''

    vs_prev_label = f'v/s {prev_week_label}'

    # ── Trend insight: Item accuracy ──
    cur_item_acc_avg = round(sum(trend_item_acc) / len(trend_item_acc), 2)
    prev_item_acc_avg = (round(sum(prev_item_acc_values) / len(prev_item_acc_values), 2)
                         if prev_item_acc_values else None)
    d1, c1, p1 = _fmt_change_acc(cur_item_acc_avg, prev_item_acc_avg)
    insight_trend_item = f'''<div class="insight-bar">
        {_build_insight_html(vs_prev_label, d1, c1, p1, is_acc=True)}
    </div>'''

    # ── Trend insight: SKU accuracy ──
    cur_sku_acc_avg = round(sum(trend_sku_acc) / len(trend_sku_acc), 2)
    prev_sku_acc_avg = (round(sum(prev_sku_acc_values) / len(prev_sku_acc_values), 2)
                        if prev_sku_acc_values else None)
    d1, c1, p1 = _fmt_change_acc(cur_sku_acc_avg, prev_sku_acc_avg)
    insight_trend_sku = f'''<div class="insight-bar">
        {_build_insight_html(vs_prev_label, d1, c1, p1, is_acc=True)}
    </div>'''

    # ── Trend insight: KG accuracy ──
    cur_kg_acc_avg = round(sum(trend_kg_acc) / len(trend_kg_acc), 2)
    prev_kg_acc_avg = (round(sum(prev_kg_acc_values) / len(prev_kg_acc_values), 2)
                       if prev_kg_acc_values else None)
    d1, c1, p1 = _fmt_change_acc(cur_kg_acc_avg, prev_kg_acc_avg)
    insight_trend_kg = f'''<div class="insight-bar">
        {_build_insight_html(vs_prev_label, d1, c1, p1, is_acc=True)}
    </div>'''

    # ── Pie insight: Item qty ──
    cur_total_item = total_kfm_item
    prev_total_item_avg = (round(sum(prev_total_items) / len(prev_total_items))
                           if prev_total_items else None)
    d1, c1, p1 = _fmt_change_qty(cur_total_item, prev_total_item_avg)
    insight_pie_item = f'''<div class="insight-bar">
        {_build_insight_html(vs_prev_label, d1, c1, p1, is_acc=False)}
    </div>'''

    # ── Pie insight: KG qty ──
    cur_total_kg = total_kfm_kg
    prev_total_kg_avg = (round(sum(prev_total_kgs) / len(prev_total_kgs), 2)
                         if prev_total_kgs else None)
    d1, c1, p1 = _fmt_change_qty(cur_total_kg, prev_total_kg_avg)
    insight_pie_kg = f'''<div class="insight-bar">
        {_build_insight_html(vs_prev_label, d1, c1, p1, is_acc=False)}
    </div>'''

    # ── Pie data ──
    pie_labels = [cat_labels[c] for c in cats]
    pie_item_values = [last_day_stats['categories'][c]['item_KFM'] for c in cats]
    pie_kg_values = [round(last_day_stats['categories'][c]['kg_KFM'], 2) for c in cats]
    pie_colors = [cat_colors[c] for c in cats]

    # ── Generate static fallback chart images ──
    print("  Generating static chart images for weekly report...")
    fallback_chart_item = generate_combo_chart_image(
        trend_dates, trend_item_kfm, trend_item_aba, trend_item_acc, 'Số lượng Item')
    fallback_chart_sku = generate_combo_chart_image(
        trend_dates, trend_sku_kfm, trend_sku_aba, trend_sku_acc, 'Số SKU')
    fallback_chart_kg = generate_combo_chart_image(
        trend_dates, trend_kg_kfm, trend_kg_aba, trend_kg_acc, 'Trọng lượng (KG)')
    fallback_pie_item = generate_pie_chart_image(
        pie_labels, pie_item_values, pie_colors, 'Item')
    fallback_pie_kg = generate_pie_chart_image(
        pie_labels, pie_kg_values, pie_colors, 'KG')

    # Category stacked charts
    cat_colors_map = {'ĐÔNG': '#60a5fa', 'MÁT': '#34d399', 'TCNK': '#fbbf24'}
    cat_labels_map = {'ĐÔNG': 'Hàng Đông', 'MÁT': 'Hàng Mát', 'TCNK': 'TCNK'}
    fallback_cat_item = generate_stacked_chart_image(
        trend_dates, trend_cat_item, cat_colors_map, cat_labels_map, 'Số lượng Item')
    fallback_cat_kg = generate_stacked_chart_image(
        trend_dates, trend_cat_kg, cat_colors_map, cat_labels_map, 'Trọng lượng (KG)')
    print("  ✓ Static chart images generated")

    # ── Compute accuracy averages for auto comment ──
    acc_averages = {
        'item': math.floor(sum(trend_item_acc) / len(trend_item_acc) * 100) / 100 if trend_item_acc else 0,
        'sku': math.floor(sum(trend_sku_acc) / len(trend_sku_acc) * 100) / 100 if trend_sku_acc else 0,
        'kg': math.floor(sum(trend_kg_acc) / len(trend_kg_acc) * 100) / 100 if trend_kg_acc else 0,
    }
    prev_acc_averages = {
        'item': math.floor(sum(prev_item_acc_values) / len(prev_item_acc_values) * 100) / 100 if prev_item_acc_values else None,
        'sku': math.floor(sum(prev_sku_acc_values) / len(prev_sku_acc_values) * 100) / 100 if prev_sku_acc_values else None,
        'kg': math.floor(sum(prev_kg_acc_values) / len(prev_kg_acc_values) * 100) / 100 if prev_kg_acc_values else None,
    }

    # ── Auto comment ──
    auto_comment_html = generate_auto_comment(
        weekly_rows, acc_averages, prev_acc_averages,
        week_label, prev_week_label,
        weekly_detail_items_all)

    # ── Consolidated discrepancy detail table ──
    # Aggregate: barcode -> {ten_hang, dvt, days_count, total_thua, total_thieu, dates}
    barcode_agg = {}
    for date_key in sorted(weekly_detail_items_all.keys()):
        items = weekly_detail_items_all[date_key]
        date_str = datetime.strptime(date_key, '%Y-%m-%d').strftime('%d/%m')
        for it in items:
            bc = it['barcode']
            if bc not in barcode_agg:
                barcode_agg[bc] = {
                    'ten_hang': it['ten_hang'],
                    'dvt': it['dvt'],
                    'days_count': 0,
                    'total_thua': 0,
                    'total_thieu': 0,
                    'dates': [],
                }
            agg = barcode_agg[bc]
            if date_str not in agg['dates']:
                agg['days_count'] += 1
                agg['dates'].append(date_str)
            agg['total_thua'] += (it['chenh_lech_thua'] or 0)
            agg['total_thieu'] += (it['chenh_lech_thieu'] or 0)

    # Sort by days_count desc, then total discrepancy desc
    sorted_barcodes = sorted(
        barcode_agg.items(),
        key=lambda x: (x[1]['days_count'], x[1]['total_thua'] + x[1]['total_thieu']),
        reverse=True
    )

    # ── Build HTML ──
    date_range_str = f"{week_monday.strftime('%d/%m')} — {week_sunday.strftime('%d/%m/%Y')}"

    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Đối Soát Tồn Kho Tuần {week_full_label} — KFM vs ABA</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-card: rgba(30, 41, 59, 0.7);
            --bg-glass: rgba(255, 255, 255, 0.03);
            --border-glass: rgba(255, 255, 255, 0.08);
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --accent-blue: #60a5fa;
            --accent-green: #34d399;
            --accent-yellow: #fbbf24;
            --accent-purple: #a78bfa;
            --accent-pink: #f472b6;
            --accent-red: #f87171;
            --gradient-1: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --gradient-2: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            --gradient-3: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        html {{
            overflow-x: hidden;
            width: 100%;
        }}

        body {{
            font-family: 'Inter', -apple-system, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            line-height: 1.6;
            overflow-x: hidden;
            width: 100%;
            -webkit-text-size-adjust: 100%;
        }}

        .bg-pattern {{
            position: fixed;
            inset: 0;
            background:
                radial-gradient(ellipse at 20% 20%, rgba(96, 165, 250, 0.08) 0%, transparent 50%),
                radial-gradient(ellipse at 80% 80%, rgba(167, 139, 250, 0.06) 0%, transparent 50%),
                radial-gradient(ellipse at 50% 50%, rgba(52, 211, 153, 0.04) 0%, transparent 50%);
            pointer-events: none;
            z-index: 0;
        }}

        .container {{
            max-width: 1100px;
            margin: 0 auto;
            padding: 2rem 3rem;
            position: relative;
            z-index: 1;
            width: 100%;
        }}

        /* Header */
        .header {{
            text-align: center;
            margin-bottom: 3rem;
            padding: 2.5rem 2rem;
            background: #1e293b;
            border: 1px solid var(--border-glass);
            border-radius: 24px;
            position: relative;
            overflow: hidden;
        }}
        .header::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--accent-blue), var(--accent-purple), var(--accent-pink));
        }}
        .header h1 {{
            font-size: 2rem;
            font-weight: 800;
            background: linear-gradient(135deg, #f1f5f9, #94a3b8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
            letter-spacing: -0.02em;
        }}
        .header .subtitle {{
            color: var(--text-secondary);
            font-size: 1.05rem;
            font-weight: 400;
        }}
        .header .date-badge {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            margin-top: 1rem;
            padding: 0.5rem 1.25rem;
            background: rgba(96, 165, 250, 0.1);
            border: 1px solid rgba(96, 165, 250, 0.2);
            border-radius: 100px;
            font-size: 0.9rem;
            font-weight: 600;
            color: var(--accent-blue);
        }}

        /* Cards */
        .card {{
            background: #1e293b;
            border: 1px solid var(--border-glass);
            border-radius: 20px;
            padding: 2rem;
            margin-bottom: 2rem;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}
        .card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }}
        .card-title {{
            font-size: 1.25rem;
            font-weight: 700;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}
        .card-title .icon {{
            width: 36px;
            height: 36px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.1rem;
        }}

        /* Summary Cards */
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .summary-item {{
            padding: 1.5rem;
            border-radius: 16px;
            background: var(--bg-glass);
            border: 1px solid var(--border-glass);
            text-align: center;
        }}
        .summary-item .label {{
            font-size: 0.8rem;
            font-weight: 500;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
        }}
        .summary-item .value {{
            font-size: 1.8rem;
            font-weight: 800;
            letter-spacing: -0.02em;
        }}
        .summary-item .sub {{
            font-size: 0.75rem;
            color: var(--text-muted);
            margin-top: 0.25rem;
        }}

        /* Table */
        .table-wrapper {{
            overflow-x: auto;
            border-radius: 12px;
            border: 1px solid var(--border-glass);
            max-width: 100%;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
        }}
        thead th {{
            background: rgba(255, 255, 255, 0.04);
            padding: 0.85rem 1rem;
            text-align: center;
            font-weight: 600;
            color: var(--text-secondary);
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border-bottom: 1px solid var(--border-glass);
            white-space: nowrap;
        }}
        thead th:first-child {{
            text-align: left;
        }}
        thead th.group-header {{
            border-bottom: none;
            padding-bottom: 0.4rem;
        }}
        thead th.sub-header {{
            font-size: 0.72rem;
            padding-top: 0.3rem;
            color: var(--text-muted);
            text-align: center !important;
        }}
        tbody td {{
            padding: 0.85rem 1rem;
            text-align: center;
            border-bottom: 1px solid rgba(255, 255, 255, 0.03);
        }}
        tbody td:first-child {{
            text-align: left;
            font-weight: 600;
        }}
        tbody tr:hover {{
            background: rgba(255, 255, 255, 0.02);
        }}
        tbody tr:last-child td {{
            border-bottom: none;
        }}
        .row-total {{
            background: rgba(255, 255, 255, 0.03);
            font-weight: 700 !important;
        }}
        .row-total td {{
            font-weight: 700;
            border-top: 2px solid var(--border-glass);
        }}
        .cat-dot {{
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 8px;
        }}

        /* Weekly Table */
        .weekly-header {{
            display: flex;
            align-items: center;
            gap: 1rem;
            margin-bottom: 1.5rem;
        }}
        .weekly-header h3 {{
            font-size: 1.1rem;
            font-weight: 700;
            color: var(--accent-red);
            font-style: italic;
        }}
        .week-badge {{
            display: inline-flex;
            align-items: center;
            padding: 0.35rem 1rem;
            background: rgba(248, 113, 113, 0.12);
            border: 1px solid rgba(248, 113, 113, 0.25);
            border-radius: 8px;
            font-size: 0.85rem;
            font-weight: 700;
            color: var(--accent-red);
        }}
        .row-avg {{
            background: rgba(255, 255, 255, 0.03);
        }}
        .row-avg td {{
            font-weight: 600;
            color: var(--accent-red);
            font-style: italic;
            border-top: 2px solid var(--border-glass);
        }}
        .no-data td {{
            color: var(--text-muted);
        }}

        /* Insight Badges */
        .insight-bar {{
            display: flex;
            gap: 1rem;
            margin-top: 1.25rem;
            flex-wrap: wrap;
        }}
        .insight-badge {{
            flex: 1;
            min-width: 180px;
            padding: 0.85rem 1rem;
            border-radius: 12px;
            background: var(--bg-glass);
            border: 1px solid var(--border-glass);
        }}
        .insight-label {{
            font-size: 0.72rem;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin-bottom: 0.35rem;
        }}
        .insight-value {{
            font-size: 1.15rem;
            font-weight: 800;
            letter-spacing: -0.01em;
        }}
        .insight-detail {{
            font-size: 0.72rem;
            color: var(--text-muted);
            margin-top: 0.2rem;
        }}

        /* Chart Fallback Images */
        .chart-fallback {{
            width: 100%;
            height: auto;
            border-radius: 8px;
            display: block;
        }}
        .pie-chart-container .chart-fallback {{
            max-width: 320px;
            margin: 0 auto;
        }}

        /* Charts Grid */
        .charts-grid {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 2rem;
        }}
        .chart-container {{
            position: relative;
            height: 380px;
            width: 100%;
            isolation: isolate;
        }}
        .pie-section {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
            align-items: center;
        }}
        .pie-chart-container {{
            position: relative;
            height: 350px;
            display: flex;
            justify-content: center;
            isolation: isolate;
        }}
        .pie-legend {{
            display: flex;
            flex-direction: column;
            gap: 1.25rem;
        }}
        .pie-legend-item {{
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 1rem 1.25rem;
            border-radius: 12px;
            background: var(--bg-glass);
            border: 1px solid var(--border-glass);
        }}
        .pie-legend-dot {{
            width: 14px;
            height: 14px;
            border-radius: 50%;
            flex-shrink: 0;
        }}
        .pie-legend-label {{
            font-weight: 500;
            color: var(--text-secondary);
            font-size: 0.85rem;
        }}
        .pie-legend-value {{
            margin-left: auto;
            font-weight: 700;
            font-size: 1.05rem;
        }}
        .pie-legend-pct {{
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-left: 0.5rem;
        }}

        /* Auto Comment */
        .comment-card {{
            background: linear-gradient(135deg, rgba(167, 139, 250, 0.08), rgba(96, 165, 250, 0.05));
            border: 1px solid rgba(167, 139, 250, 0.2);
        }}

        /* Frequency badge */
        .freq-badge {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 28px;
            height: 24px;
            padding: 0 6px;
            border-radius: 6px;
            font-size: 0.78rem;
            font-weight: 700;
        }}
        .freq-low {{ background: rgba(52, 211, 153, 0.15); color: var(--accent-green); }}
        .freq-mid {{ background: rgba(251, 191, 36, 0.15); color: var(--accent-yellow); }}
        .freq-high {{ background: rgba(248, 113, 113, 0.15); color: var(--accent-red); }}

        /* Footer */
        .footer {{
            text-align: center;
            padding: 2rem;
            color: var(--text-muted);
            font-size: 0.8rem;
        }}

        /* Tablet */
        @media (max-width: 1024px) {{
            .pie-section {{
                grid-template-columns: 1fr;
                gap: 1.5rem;
            }}
            .pie-chart-container {{
                height: 300px;
            }}
        }}

        /* Mobile */
        @media (max-width: 768px) {{
            .container {{
                padding: 0.75rem;
            }}
            .header {{
                padding: 1.5rem 1rem;
                margin-bottom: 1.5rem;
                border-radius: 16px;
            }}
            .header h1 {{
                font-size: 1.25rem;
            }}
            .header .subtitle {{
                font-size: 0.9rem;
            }}
            .header .date-badge {{
                font-size: 0.8rem;
                padding: 0.4rem 1rem;
            }}
            .summary-grid {{
                grid-template-columns: repeat(2, 1fr);
                gap: 0.75rem;
                margin-bottom: 1.25rem;
            }}
            .summary-item {{
                padding: 1rem;
                border-radius: 12px;
            }}
            .summary-item .value {{
                font-size: 1.35rem;
            }}
            .summary-item .label {{
                font-size: 0.7rem;
            }}
            .card {{
                padding: 1.25rem 1rem;
                margin-bottom: 1.25rem;
                border-radius: 14px;
            }}
            .card-title {{
                font-size: 1rem;
                flex-wrap: wrap;
                gap: 0.5rem;
                margin-bottom: 1rem;
            }}
            .card-title .icon {{
                width: 30px;
                height: 30px;
                font-size: 0.95rem;
                flex-shrink: 0;
            }}
            .chart-container {{
                height: 280px;
            }}
            .pie-section {{
                grid-template-columns: 1fr;
                gap: 1.25rem;
            }}
            .pie-chart-container {{
                height: 260px;
            }}
            .pie-legend {{
                gap: 0.75rem;
            }}
            .pie-legend-item {{
                padding: 0.75rem 1rem;
                gap: 0.75rem;
            }}
            .pie-legend-label {{
                font-size: 0.8rem;
            }}
            .pie-legend-value {{
                font-size: 0.9rem;
            }}
            .pie-legend-pct {{
                font-size: 0.7rem;
            }}
            table {{
                font-size: 0.8rem;
            }}
            thead th {{
                padding: 0.6rem 0.5rem;
                font-size: 0.7rem;
            }}
            tbody td {{
                padding: 0.6rem 0.5rem;
            }}
            .weekly-header {{
                flex-wrap: wrap;
                gap: 0.75rem;
                margin-bottom: 1rem;
            }}
            .week-badge {{
                font-size: 0.75rem;
                padding: 0.25rem 0.75rem;
            }}
            .footer {{
                padding: 1.25rem;
                font-size: 0.7rem;
            }}
        }}

        /* Small mobile */
        @media (max-width: 400px) {{
            .summary-grid {{
                grid-template-columns: 1fr;
            }}
            .summary-item .value {{
                font-size: 1.2rem;
            }}
            .chart-container {{
                height: 240px;
            }}
            .pie-chart-container {{
                height: 220px;
            }}
            .card-title {{
                font-size: 0.9rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="bg-pattern"></div>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>📦 Đối Soát Tồn Kho Tuần {week_label}</h1>
            <p class="subtitle">Báo cáo kiểm soát tồn kho hàng tuần — KFM vs ABA</p>
            <div class="date-badge">
                📅 {date_range_str}
            </div>
        </div>

        <!-- Summary Cards -->
        <div class="summary-grid">
            <div class="summary-item">
                <div class="label">Tổng SKU</div>
                <div class="value" style="color: var(--accent-purple)">{total_kfm_sku:,}</div>
                <div class="sub">Cuối tuần {week_label}</div>
            </div>
            <div class="summary-item">
                <div class="label">Tồn KFM (Item)</div>
                <div class="value" style="color: var(--accent-blue)">{total_kfm_item:,}</div>
                <div class="sub">Cuối tuần {week_label}</div>
            </div>
            <div class="summary-item">
                <div class="label">Tồn ABA (Item)</div>
                <div class="value" style="color: var(--accent-green)">{total_aba_item:,}</div>
                <div class="sub">Cuối tuần {week_label}</div>
            </div>
            <div class="summary-item">
                <div class="label">Tổng KG (KFM)</div>
                <div class="value" style="color: var(--accent-yellow)">{total_kfm_kg:,.2f}</div>
                <div class="sub">Cuối tuần {week_label}</div>
            </div>
            <div class="summary-item">
                <div class="label">TB Chính Xác (Item)</div>
                <div class="value" style="color: {'var(--accent-green)' if avg_acc >= 99.5 else 'var(--accent-red)'}">{avg_acc:.2f}%</div>
                <div class="sub">{'✅ Tốt' if avg_acc >= 99.5 else '⚠️ Cần kiểm tra'}</div>
            </div>
        </div>

        <!-- Section: Weekly Summary Table -->
        <div class="card" id="section-weekly">
            <div class="weekly-header">
                <div class="card-title" style="margin-bottom: 0;">
                    <div class="icon" style="background: rgba(248, 113, 113, 0.15); color: var(--accent-red);">📋</div>
                    <span style="font-style: italic; color: var(--accent-red);">BÁO CÁO TỒN KHO</span>
                </div>
                <div class="week-badge">{week_full_label}</div>
            </div>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th style="text-align: center;">Thứ</th>
                            <th>Ngày</th>
                            <th>Tỷ lệ tồn kho chính xác</th>
                            <th>Lệch dương</th>
                            <th>Lệch âm</th>
                            <th>Tổng lệch</th>
                            <th>Tồn KDB</th>
                        </tr>
                    </thead>
                    <tbody>
"""

    for wr in weekly_rows:
        if wr['has_data']:
            html += f"""                        <tr>
                            <td style="text-align: center; font-weight: 500;">{wr['thu']}</td>
                            <td style="text-align: center;">{wr['ngay']}</td>
                            <td style="text-align: center; font-weight: 600; color: {'var(--accent-green)' if wr['acc'] >= 99.5 else 'var(--accent-red)'};">{wr['acc']:.2f}%</td>
                            <td style="text-align: center;">{wr['lech_duong']:,}</td>
                            <td style="text-align: center;">{wr['lech_am']:,}</td>
                            <td style="text-align: center;">{wr['tong_lech']:,}</td>
                            <td style="text-align: center;">{wr['ton_kdb']:,}</td>
                        </tr>
"""
        else:
            html += f"""                        <tr class="no-data">
                            <td style="text-align: center; font-weight: 500;">{wr['thu']}</td>
                            <td style="text-align: center;">{wr['ngay']}</td>
                            <td style="text-align: center;"></td>
                            <td style="text-align: center;">0</td>
                            <td style="text-align: center;">0</td>
                            <td style="text-align: center;">0</td>
                            <td style="text-align: center;">0</td>
                        </tr>
"""

    html += f"""                        <tr class="row-avg">
                            <td colspan="2" style="text-align: center; font-style: italic;">Trung bình tỷ lệ tồn kho chính xác</td>
                            <td style="text-align: center; font-weight: 700;">{avg_acc:.2f}%</td>
                            <td colspan="4"></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Section: Stats Table by Category -->
        <div class="card" id="section-stats">
            <div class="card-title">
                <div class="icon" style="background: rgba(96, 165, 250, 0.15); color: var(--accent-blue);">📊</div>
                Thống Kê Sản Lượng Theo Phân Nhóm — Cuối {week_label}
            </div>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th rowspan="2" style="vertical-align: middle;">Phân nhóm</th>
                            <th rowspan="2" style="vertical-align: middle;">Số SKU</th>
                            <th colspan="2" class="group-header" style="color: var(--accent-blue);">Tồn kho (Item)</th>
                            <th colspan="2" class="group-header" style="color: var(--accent-yellow);">Trọng lượng (KG)</th>
                        </tr>
                        <tr>
                            <th class="sub-header">KFM</th>
                            <th class="sub-header">ABA</th>
                            <th class="sub-header">KFM</th>
                            <th class="sub-header">ABA</th>
                        </tr>
                    </thead>
                    <tbody>
"""
    for r in table_rows:
        html += f"""                        <tr>
                            <td><span class="cat-dot" style="background: {r['color']}"></span>{r['cat']}</td>
                            <td>{r['sku']:,}</td>
                            <td>{r['item_KFM']:,}</td>
                            <td>{r['item_ABA']:,}</td>
                            <td>{r['kg_KFM']:,.2f}</td>
                            <td>{r['kg_ABA']:,.2f}</td>
                        </tr>
"""

    html += f"""                        <tr class="row-total">
                            <td>Tổng cộng</td>
                            <td>{total_kfm_sku:,}</td>
                            <td>{total_kfm_item:,}</td>
                            <td>{total_aba_item:,}</td>
                            <td>{total_kfm_kg:,.2f}</td>
                            <td>{total_aba_kg:,.2f}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Section: Trend Item -->
        <div class="card" id="section-trend-item">
            <div class="card-title">
                <div class="icon" style="background: rgba(167, 139, 250, 0.15); color: var(--accent-purple);">📈</div>
                Trend Tỷ Lệ Chính Xác Theo Item — {week_label}
            </div>
            <div class="chart-container">
                <img class="chart-fallback" id="fallback-chartItem" src="data:image/png;base64,{fallback_chart_item}" alt="Trend Item Chart">
                <canvas id="chartItem" style="display:none;"></canvas>
            </div>
            {insight_trend_item}
        </div>

        <!-- Section: Trend SKU -->
        <div class="card" id="section-trend-sku">
            <div class="card-title">
                <div class="icon" style="background: rgba(167, 139, 250, 0.15); color: var(--accent-purple);">📈</div>
                Trend Tỷ Lệ Chính Xác Theo SKU — {week_label}
            </div>
            <div class="chart-container">
                <img class="chart-fallback" id="fallback-chartSku" src="data:image/png;base64,{fallback_chart_sku}" alt="Trend SKU Chart">
                <canvas id="chartSku" style="display:none;"></canvas>
            </div>
            {insight_trend_sku}
        </div>

        <!-- Section: Trend KG -->
        <div class="card" id="section-trend-kg">
            <div class="card-title">
                <div class="icon" style="background: rgba(167, 139, 250, 0.15); color: var(--accent-purple);">📈</div>
                Trend Tỷ Lệ Chính Xác Theo KG — {week_label}
            </div>
            <div class="chart-container">
                <img class="chart-fallback" id="fallback-chartKg" src="data:image/png;base64,{fallback_chart_kg}" alt="Trend KG Chart">
                <canvas id="chartKg" style="display:none;"></canvas>
            </div>
            {insight_trend_kg}
        </div>

        <!-- Section: Pie Chart - Items -->
        <div class="card" id="section-pie-item">
            <div class="card-title">
                <div class="icon" style="background: rgba(167, 139, 250, 0.15); color: var(--accent-purple);">🥧</div>
                Tỉ Trọng Theo Số Lượng (Item) — KFM — Cuối {week_label}
            </div>
            <div class="pie-section">
                <div class="pie-chart-container">
                    <img class="chart-fallback" id="fallback-chartPieItem" src="data:image/png;base64,{fallback_pie_item}" alt="Pie Item Chart">
                    <canvas id="chartPieItem" style="display:none;"></canvas>
                </div>
                <div class="pie-legend" id="pieLegendItem"></div>
            </div>
            {insight_pie_item}
        </div>

        <!-- Section: Pie Chart - KG -->
        <div class="card" id="section-pie-kg">
            <div class="card-title">
                <div class="icon" style="background: rgba(251, 191, 36, 0.15); color: var(--accent-yellow);">🥧</div>
                Tỉ Trọng Theo Trọng Lượng (KG) — KFM — Cuối {week_label}
            </div>
            <div class="pie-section">
                <div class="pie-chart-container">
                    <img class="chart-fallback" id="fallback-chartPieKg" src="data:image/png;base64,{fallback_pie_kg}" alt="Pie KG Chart">
                    <canvas id="chartPieKg" style="display:none;"></canvas>
                </div>
                <div class="pie-legend" id="pieLegendKg"></div>
            </div>
            {insight_pie_kg}
        </div>

        <!-- Section: Category Trend Item -->
        <div class="card" id="section-cat-item">
            <div class="card-title">
                <div class="icon" style="background: rgba(52, 211, 153, 0.15); color: var(--accent-green);">📊</div>
                Biến Động Sản Lượng Theo Nhóm (Item) — {week_label}
            </div>
            <div class="chart-container">
                <img class="chart-fallback" id="fallback-chartCatItem" src="data:image/png;base64,{fallback_cat_item}" alt="Category Item Trend">
                <canvas id="chartCatItem" style="display:none;"></canvas>
            </div>
        </div>

        <!-- Section: Category Trend KG -->
        <div class="card" id="section-cat-kg">
            <div class="card-title">
                <div class="icon" style="background: rgba(251, 191, 36, 0.15); color: var(--accent-yellow);">📊</div>
                Biến Động Sản Lượng Theo Nhóm (KG) — {week_label}
            </div>
            <div class="chart-container">
                <img class="chart-fallback" id="fallback-chartCatKg" src="data:image/png;base64,{fallback_cat_kg}" alt="Category KG Trend">
                <canvas id="chartCatKg" style="display:none;"></canvas>
            </div>
        </div>

        <!-- Section: Auto Comment -->
        <div class="card comment-card" id="section-comment">
            <div class="card-title">
                <div class="icon" style="background: rgba(167, 139, 250, 0.15); color: var(--accent-purple);">📝</div>
                Nhận Xét Tuần {week_label}
            </div>
            {auto_comment_html}
        </div>
"""

    # ── Section: Consolidated Discrepancy Detail Table ──
    if sorted_barcodes:
        html += f"""
        <!-- Section: Consolidated Discrepancy Detail -->
        <div class="card" id="section-detail">
            <div class="card-title">
                <div class="icon" style="background: rgba(248, 113, 113, 0.15); color: var(--accent-red);">🔍</div>
                Chi Tiết Mã Bị Lệch — Tổng Hợp {week_label}
            </div>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th style="text-align: center; width: 40px;">STT</th>
                            <th style="text-align: left;">Barcode</th>
                            <th style="text-align: left;">Tên hàng</th>
                            <th style="text-align: center;">ĐVT</th>
                            <th style="text-align: center;">Số ngày lệch</th>
                            <th style="text-align: center;">Tổng thừa</th>
                            <th style="text-align: center;">Tổng thiếu</th>
                            <th style="text-align: left;">Ngày lệch</th>
                        </tr>
                    </thead>
                    <tbody>
"""
        for idx, (bc, agg) in enumerate(sorted_barcodes, 1):
            # Frequency badge color
            if agg['days_count'] >= 5:
                freq_class = 'freq-high'
            elif agg['days_count'] >= 3:
                freq_class = 'freq-mid'
            else:
                freq_class = 'freq-low'

            thua_style = 'color: var(--accent-green); font-weight: 600;' if agg['total_thua'] else ''
            thieu_style = 'color: var(--accent-red); font-weight: 600;' if agg['total_thieu'] else ''
            dates_str = ', '.join(agg['dates'])

            html += f"""                        <tr>
                            <td style="text-align: center;">{idx}</td>
                            <td style="text-align: left; font-family: monospace; font-size: 0.82rem;">{bc}</td>
                            <td style="text-align: left;">{agg['ten_hang']}</td>
                            <td style="text-align: center;">{agg['dvt']}</td>
                            <td style="text-align: center;"><span class="freq-badge {freq_class}">{agg['days_count']}</span></td>
                            <td style="text-align: center; {thua_style}">{agg['total_thua'] if agg['total_thua'] else ''}</td>
                            <td style="text-align: center; {thieu_style}">{agg['total_thieu'] if agg['total_thieu'] else ''}</td>
                            <td style="text-align: left; font-size: 0.82rem; color: var(--text-secondary);">{dates_str}</td>
                        </tr>
"""

        html += f"""                    </tbody>
                </table>
            </div>
            <div style="margin-top: 1rem; padding: 0.75rem 1rem; border-radius: 10px; background: var(--bg-glass); border: 1px solid var(--border-glass); display: flex; align-items: center; gap: 0.75rem;">
                <span style="font-size: 1.1rem;">⚠️</span>
                <span style="font-size: 0.85rem; color: var(--text-secondary);">Tổng số mã lệch trong tuần: <strong style="color: var(--accent-red);">{len(sorted_barcodes)}</strong> SKU · Mã lệch ≥ 3 ngày: <strong style="color: var(--accent-red);">{len([b for b in sorted_barcodes if b[1]['days_count'] >= 3])}</strong></span>
            </div>
        </div>
"""

    html += f"""
        <div class="footer">
            <p>Generated at {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} • KFM × ABA Weekly Inventory Reconciliation • {week_full_label}</p>
        </div>
    </div>

    <script>
        // Chart.js defaults
        Chart.defaults.color = '#94a3b8';
        Chart.defaults.borderColor = 'rgba(255,255,255,0.05)';
        Chart.defaults.font.family = "'Inter', sans-serif";
        Chart.register(ChartDataLabels);
        Chart.defaults.plugins.datalabels = {{ display: false }};

        const dates = {json.dumps(trend_dates)};

        // Utility: Create combo chart (bars + line)
        function createComboChart(canvasId, kfmData, abaData, accData, yLabel) {{
            const ctx = document.getElementById(canvasId).getContext('2d');
            new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: dates,
                    datasets: [
                        {{
                            label: 'KFM',
                            data: kfmData,
                            backgroundColor: 'rgba(96, 165, 250, 0.6)',
                            borderColor: 'rgba(96, 165, 250, 1)',
                            borderWidth: 1,
                            borderRadius: 6,
                            order: 2,
                            yAxisID: 'y',
                        }},
                        {{
                            label: 'ABA',
                            data: abaData,
                            backgroundColor: 'rgba(52, 211, 153, 0.6)',
                            borderColor: 'rgba(52, 211, 153, 1)',
                            borderWidth: 1,
                            borderRadius: 6,
                            order: 2,
                            yAxisID: 'y',
                        }},
                        {{
                            label: 'Tỷ lệ chính xác (%)',
                            data: accData,
                            type: 'line',
                            borderColor: '#f472b6',
                            backgroundColor: 'rgba(244, 114, 182, 0.1)',
                            borderWidth: 3,
                            pointBackgroundColor: '#f472b6',
                            pointBorderColor: '#fff',
                            pointBorderWidth: 2,
                            pointRadius: 5,
                            pointHoverRadius: 7,
                            tension: 0.35,
                            fill: false,
                            order: 1,
                            yAxisID: 'y1',
                            clip: false,
                            datalabels: {{
                                display: true,
                                align: 'top',
                                anchor: 'end',
                                offset: 6,
                                color: '#f472b6',
                                font: {{ size: 11, weight: 'bold' }},
                                formatter: function(value) {{ return value.toFixed(2) + '%'; }}
                            }}
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    layout: {{
                        padding: {{ top: 40 }}
                    }},
                    interaction: {{
                        mode: 'index',
                        intersect: false,
                    }},
                    plugins: {{
                        legend: {{
                            position: 'bottom',
                            labels: {{
                                usePointStyle: true,
                                pointStyle: 'circle',
                                padding: 20,
                                font: {{ size: 12, weight: '500' }}
                            }}
                        }},
                        tooltip: {{
                            backgroundColor: 'rgba(15, 23, 42, 0.95)',
                            titleFont: {{ size: 13, weight: '600' }},
                            bodyFont: {{ size: 12 }},
                            padding: 14,
                            cornerRadius: 10,
                            borderColor: 'rgba(255,255,255,0.1)',
                            borderWidth: 1,
                            callbacks: {{
                                label: function(ctx) {{
                                    if (ctx.dataset.yAxisID === 'y1') {{
                                        return ctx.dataset.label + ': ' + ctx.parsed.y.toFixed(2) + '%';
                                    }}
                                    return ctx.dataset.label + ': ' + ctx.parsed.y.toLocaleString();
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        x: {{
                            grid: {{ display: false }},
                            ticks: {{ font: {{ size: 11, weight: '500' }} }}
                        }},
                        y: {{
                            position: 'left',
                            title: {{
                                display: true,
                                text: yLabel,
                                font: {{ size: 12, weight: '600' }},
                                color: '#64748b'
                            }},
                            grid: {{ color: 'rgba(255,255,255,0.04)' }},
                            ticks: {{
                                font: {{ size: 11 }},
                                callback: function(v) {{ return v.toLocaleString(); }}
                            }}
                        }},
                        y1: {{
                            position: 'right',
                            min: 0,
                            max: 100,
                            title: {{
                                display: true,
                                text: 'Tỷ lệ chính xác (%)',
                                font: {{ size: 12, weight: '600' }},
                                color: '#f472b6'
                            }},
                            grid: {{ drawOnChartArea: false }},
                            ticks: {{
                                font: {{ size: 11 }},
                                callback: function(v) {{ return v + '%'; }}
                            }}
                        }}
                    }}
                }}
            }});
            // Show interactive canvas, hide static fallback
            document.getElementById(canvasId).style.display = 'block';
            var fb = document.getElementById('fallback-' + canvasId);
            if (fb) fb.style.display = 'none';
        }}

        // Create charts
        createComboChart('chartItem',
            {json.dumps(trend_item_kfm)},
            {json.dumps(trend_item_aba)},
            {json.dumps(trend_item_acc)},
            'Số lượng Item'
        );
        createComboChart('chartSku',
            {json.dumps(trend_sku_kfm)},
            {json.dumps(trend_sku_aba)},
            {json.dumps(trend_sku_acc)},
            'Số SKU'
        );
        createComboChart('chartKg',
            {json.dumps(trend_kg_kfm)},
            {json.dumps(trend_kg_aba)},
            {json.dumps(trend_kg_acc)},
            'Trọng lượng (KG)'
        );

        // Reusable pie chart creator
        const pieLabels = {json.dumps(pie_labels)};
        const pieColors = {json.dumps(pie_colors)};

        function createPieChart(canvasId, legendId, values, unit) {{
            const total = values.reduce((a, b) => a + b, 0);
            const ctx = document.getElementById(canvasId).getContext('2d');
            new Chart(ctx, {{
                type: 'doughnut',
                data: {{
                    labels: pieLabels,
                    datasets: [{{
                        data: values,
                        backgroundColor: pieColors.map(c => c + 'cc'),
                        borderColor: pieColors,
                        borderWidth: 2,
                        hoverOffset: 12,
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '55%',
                    plugins: {{
                        legend: {{ display: false }},
                        datalabels: {{
                            display: true,
                            color: '#fff',
                            font: {{ size: 13, weight: 'bold' }},
                            formatter: function(value) {{
                                const pct = ((value / total) * 100).toFixed(1);
                                return pct + '%';
                            }},
                            anchor: 'center',
                            align: 'center',
                        }},
                        tooltip: {{
                            backgroundColor: 'rgba(15, 23, 42, 0.95)',
                            titleFont: {{ size: 13, weight: '600' }},
                            bodyFont: {{ size: 12 }},
                            padding: 14,
                            cornerRadius: 10,
                            callbacks: {{
                                label: function(ctx) {{
                                    const pct = ((ctx.parsed / total) * 100).toFixed(1);
                                    return ctx.label + ': ' + ctx.parsed.toLocaleString() + ' ' + unit + ' (' + pct + '%)';
                                }}
                            }}
                        }}
                    }}
                }}
            }});
            // Custom legend
            const legendContainer = document.getElementById(legendId);
            pieLabels.forEach((label, i) => {{
                const pct = ((values[i] / total) * 100).toFixed(1);
                const item = document.createElement('div');
                item.className = 'pie-legend-item';
                item.innerHTML = `
                    <div class="pie-legend-dot" style="background: ${{pieColors[i]}}"></div>
                    <div><div class="pie-legend-label">${{label}}</div></div>
                    <div class="pie-legend-value">${{unit === 'KG' ? values[i].toLocaleString(undefined, {{minimumFractionDigits: 2, maximumFractionDigits: 2}}) : values[i].toLocaleString()}} ${{unit}}<span class="pie-legend-pct">${{pct}}%</span></div>
                `;
                legendContainer.appendChild(item);
            }});
            // Show interactive canvas, hide static fallback
            document.getElementById(canvasId).style.display = 'block';
            var fb = document.getElementById('fallback-' + canvasId);
            if (fb) fb.style.display = 'none';
        }}

        // Create both pie charts
        createPieChart('chartPieItem', 'pieLegendItem', {json.dumps(pie_item_values)}, 'Item');
        createPieChart('chartPieKg', 'pieLegendKg', {json.dumps(pie_kg_values)}, 'KG');

        // Stacked bar chart for category trends
        function createStackedChart(canvasId, datasets, yLabel) {{
            const ctx = document.getElementById(canvasId).getContext('2d');
            new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: dates,
                    datasets: datasets
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    layout: {{ padding: {{ top: 20 }} }},
                    interaction: {{ mode: 'index', intersect: false }},
                    plugins: {{
                        legend: {{
                            position: 'bottom',
                            labels: {{
                                usePointStyle: true,
                                pointStyle: 'circle',
                                padding: 20,
                                font: {{ size: 12, weight: '500' }}
                            }}
                        }},
                        tooltip: {{
                            backgroundColor: 'rgba(15, 23, 42, 0.95)',
                            titleFont: {{ size: 13, weight: '600' }},
                            bodyFont: {{ size: 12 }},
                            padding: 14,
                            cornerRadius: 10,
                            borderColor: 'rgba(255,255,255,0.1)',
                            borderWidth: 1,
                            callbacks: {{
                                label: function(ctx) {{
                                    return ctx.dataset.label + ': ' + ctx.parsed.y.toLocaleString();
                                }},
                                footer: function(items) {{
                                    let total = 0;
                                    items.forEach(item => {{ total += item.parsed.y; }});
                                    return 'Tổng: ' + total.toLocaleString();
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        x: {{
                            stacked: true,
                            grid: {{ display: false }},
                            ticks: {{ font: {{ size: 11, weight: '500' }} }}
                        }},
                        y: {{
                            stacked: true,
                            title: {{
                                display: true,
                                text: yLabel,
                                font: {{ size: 12, weight: '600' }},
                                color: '#64748b'
                            }},
                            grid: {{ color: 'rgba(255,255,255,0.04)' }},
                            ticks: {{
                                font: {{ size: 11 }},
                                callback: function(v) {{ return v.toLocaleString(); }}
                            }}
                        }}
                    }}
                }}
            }});
            document.getElementById(canvasId).style.display = 'block';
            var fb = document.getElementById('fallback-' + canvasId);
            if (fb) fb.style.display = 'none';
        }}

        // Create category stacked charts
        createStackedChart('chartCatItem', [
            {{ label: 'Hàng Đông', data: {json.dumps(trend_cat_item['ĐÔNG'])}, backgroundColor: 'rgba(96, 165, 250, 0.6)', borderColor: '#60a5fa', borderWidth: 1, borderRadius: 4 }},
            {{ label: 'Hàng Mát', data: {json.dumps(trend_cat_item['MÁT'])}, backgroundColor: 'rgba(52, 211, 153, 0.6)', borderColor: '#34d399', borderWidth: 1, borderRadius: 4 }},
            {{ label: 'TCNK', data: {json.dumps(trend_cat_item['TCNK'])}, backgroundColor: 'rgba(251, 191, 36, 0.6)', borderColor: '#fbbf24', borderWidth: 1, borderRadius: 4 }},
        ], 'Số lượng Item');

        createStackedChart('chartCatKg', [
            {{ label: 'Hàng Đông', data: {json.dumps(trend_cat_kg['ĐÔNG'])}, backgroundColor: 'rgba(96, 165, 250, 0.6)', borderColor: '#60a5fa', borderWidth: 1, borderRadius: 4 }},
            {{ label: 'Hàng Mát', data: {json.dumps(trend_cat_kg['MÁT'])}, backgroundColor: 'rgba(52, 211, 153, 0.6)', borderColor: '#34d399', borderWidth: 1, borderRadius: 4 }},
            {{ label: 'TCNK', data: {json.dumps(trend_cat_kg['TCNK'])}, backgroundColor: 'rgba(251, 191, 36, 0.6)', borderColor: '#fbbf24', borderWidth: 1, borderRadius: 4 }},
        ], 'Trọng lượng (KG)');
    </script>
</body>
</html>"""

    return html


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='Generate weekly inventory reconciliation report')
    parser.add_argument('--week', type=str, help='Target week e.g. W15 (default: previous week)')
    parser.add_argument('--year', type=int, help='ISO year (default: current year)')
    parser.add_argument('--no-telegram', action='store_true', help='Skip Telegram sending')
    args = parser.parse_args()

    # Determine target week
    if args.week:
        target_iso_week = int(args.week.replace('W', '').replace('w', ''))
        target_iso_year = args.year or datetime.now().year
    else:
        target_iso_year, target_iso_week = get_previous_week_info()

    week_monday, week_sunday = get_week_range(target_iso_year, target_iso_week)
    print(f"📅 Target week: W{target_iso_week}-{target_iso_year} "
          f"({week_monday.strftime('%d/%m/%Y')} → {week_sunday.strftime('%d/%m/%Y')})")

    print("\n🔄 Loading master data...")
    category_map = load_master_data()
    print(f"   ✅ {len(category_map)} barcodes mapped to categories")

    print("🔄 Loading weight data...")
    weight_map = load_weight_data()
    print(f"   ✅ {len(weight_map)} barcodes with weight info")

    print("🔄 Loading reconciliation files...")
    all_days = load_doi_soat_files()
    print(f"   ✅ {len(all_days)} days loaded")

    if not all_days:
        print("❌ No data to process!")
        return

    print("\n🔄 Computing statistics...")
    daily_stats, unmatched_cat, unmatched_wt = compute_stats(all_days, category_map, weight_map)

    # Report unmatched
    if unmatched_cat:
        print(f"\n⚠️  {len(unmatched_cat)} barcode(s) không tìm được phân loại")
    if unmatched_wt:
        print(f"⚠️  {len(unmatched_wt)} barcode(s) không tìm được trọng lượng")

    # Generate HTML
    print(f"\n🔄 Generating weekly HTML report for W{target_iso_week}...")
    html = generate_weekly_html(
        daily_stats, all_days, target_iso_year, target_iso_week,
        category_map, weight_map)

    if html is None:
        print("❌ Failed to generate report!")
        return

    out_filename = f'report_doi_soat_weekly_W{target_iso_week}_{target_iso_year}.html'
    out_path = os.path.join(OUTPUT_DIR, out_filename)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"   ✅ Report saved to: {out_path}")

    print("\n🎉 Done!")


if __name__ == '__main__':
    main()
