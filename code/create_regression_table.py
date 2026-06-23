def create_regression_table_html(result, behalf_by_income_year, title="Table A1"):

    import numpy as np

    """Generate HTML table from statsmodels result"""
    
    # Build coefficient rows
    rows = []
    for i, var in enumerate(result.params.index):
        # Clean variable name
        if 'Intercept' in var:
            var_name = 'Intercept (Upper middle income)'
        elif 'High income' in var:
            var_name = 'High income'
        elif 'Low income' in var:
            var_name = 'Low income'
        elif 'Lower middle income' in var:
            var_name = 'Lower middle income'
        else:
            var_name = var
        
        # Get stats
        coef = f"{result.params.iloc[i]:.3f}"
        se = f"{result.bse.iloc[i]:.3f}"
        irr = f"{np.exp(result.params.iloc[i]):.2f}"
        ci_lower = f"{np.exp(result.conf_int()[0].iloc[i]):.2f}"
        ci_upper = f"{np.exp(result.conf_int()[1].iloc[i]):.2f}"
        z_val = f"{result.tvalues.iloc[i]:.2f}"
        p_val = f"{result.pvalues.iloc[i]:.3f}"
        
        # Significance stars
        p = result.pvalues.iloc[i]
        if p < 0.001:
            sig = '***'
        elif p < 0.01:
            sig = '**'
        elif p < 0.05:
            sig = '*'
        elif p < 0.10:
            sig = '†'
        else:
            sig = ''
        
        # Add bottom border to last row
        class_attr = ' class="bottom-border"' if i == len(result.params) - 1 else ''
        
        rows.append(f"""        <tr{class_attr}>
            <td class="var-col">{var_name}</td>
            <td>{coef}</td>
            <td>{se}</td>
            <td>{irr}</td>
            <td>({ci_lower}, {ci_upper})</td>
            <td>{z_val}</td>
            <td>{p_val}</td>
            <td>{sig}</td>
        </tr>""")
    
    rows_html = '\n'.join(rows)
    
    # Model stats
    n_obs = int(result.nobs)
    n_clusters = behalf_by_income_year['year'].nunique()
    ll = result.llf
    aic = result.aic
    bic = result.bic
    disp = result.scale
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: 'Times New Roman', Times, serif;
            margin: 40px;
        }}
        .table-title {{
            font-weight: bold;
            font-size: 14px;
            margin-bottom: 10px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin-bottom: 20px;
        }}
        th {{
            border-top: 2px solid black;
            border-bottom: 1px solid black;
            padding: 8px;
            text-align: center;
            font-weight: bold;
        }}
        td {{
            padding: 8px;
            text-align: center;
        }}
        .var-col {{
            text-align: left;
            padding-left: 20px;
        }}
        .bottom-border {{
            border-bottom: 2px solid black;
        }}
        .model-stats {{
            margin-top: 20px;
            font-size: 12px;
        }}
        .notes {{
            margin-top: 20px;
            font-size: 11px;
            line-height: 1.5;
        }}
        .notes-title {{
            font-weight: bold;
        }}
    </style>
</head>
<body>

<div class="table-title">{title}: Negative Binomial Model - 'On Behalf Of' Speaker-Turns by Income Level</div>

<table>
    <thead>
        <tr>
            <th style="text-align: left;">Variable</th>
            <th>Coefficient</th>
            <th>Std. Error</th>
            <th>IRR</th>
            <th>95% CI</th>
            <th>z</th>
            <th>p-value</th>
            <th>Sig.</th>
        </tr>
    </thead>
    <tbody>
{rows_html}
    </tbody>
</table>

<div class="model-stats">
    <div style="font-weight: bold; margin-bottom: 5px;">Model Statistics:</div>
    <div>N observations: {n_obs}</div>
    <div>N clusters (years): {n_clusters}</div>
    <div>Log-Likelihood: {ll:.2f}</div>
    <div>AIC: {aic:.2f}</div>
    <div>BIC: {bic:.2f}</div>
    <div>Dispersion: {disp:.3f}</div>
</div>

<div class="notes">
    <div class="notes-title">Notes:</div>
    <div>Reference category: Upper middle income states. Standard errors clustered by year. IRR = Incidence Rate Ratio. † p<0.10, * p<0.05, ** p<0.01, *** p<0.001</div>
</div>

</body>
</html>"""
    
    return html