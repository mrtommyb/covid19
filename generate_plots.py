# this is based heavily on
# https://github.com/JeroenKools/covid19/blob/master/COVID-19.ipynb
import requests
from io import StringIO

import pandas as pd
import datetime
import numpy as np

from bokeh.themes import Theme
from bokeh.io import curdoc
from bokeh.embed import components
from bokeh import plotting
from bokeh.models import Legend, ColumnDataSource
from bokeh.models import FuncTickFormatter, Label, Range1d
from scipy.optimize import curve_fit

import pymc3 as pm
import theano.tensor as tt
from exoplanet import optimize


theme = Theme(filename="./tomtheme.yaml")
curdoc().theme = theme


code = """
logtick = Math.log10(tick);
if ((logtick > -3) && (logtick < 3)){
    return tick.toLocaleString();
} else {
    power = Math.floor(logtick);
    retval = 10 + (power.toString()
             .split('')
             .map(function (d) { return d === '-' ? '⁻' : '⁰¹²³⁴⁵⁶⁷⁸⁹'[+d]; })
             .join(''));
    front = (tick/Math.pow(10, power)).toPrecision(2).toString().slice(0,3);
    
    if (front == '1.0'){
        return retval
    }
    else if (front.slice(1,3) == '.0'){
        return front[0] + 'x' + retval
    }
    
    return front + 'x' + retval
}
"""

confirmed_url = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_19-covid-Confirmed.csv"
deaths_url = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_19-covid-Deaths.csv"

# colorblind friendly palette from https://personal.sron.nl/~pault/
# other ideas: https://thenode.biologists.com/data-visualization-with-flying-colors/research/
colors = [
    "#228833",
    "#ee6677",
    "#4477aa",
    "#aa3377",
    "#ccbb44",
    "#aaaaaa",
    "#66ccee",
]
markers = ["circle", "square", "triangle", "diamond", "inverted_triangle"]


def get_data(dataset="confirmed"):
    r = requests.get(confirmed_url)
    str_version = StringIO(r.text)

    df = pd.read_csv(str_version, sep=",")

    # Add early data as per JeroenKools
    df.loc[df.iloc[:, 0] == "Hubei", "1/17/20"] = 45
    df.loc[df.iloc[:, 0] == "Hubei", "1/18/20"] = 62
    df.loc[df.iloc[:, 0] == "Hubei", "1/20/20"] = 218
    df = df.reindex(
        list(df.columns[:4])
        + list(
            sorted(
                df.columns[4:],
                key=lambda d: datetime.datetime.strptime(d, "%m/%d/%y"),
            )
        ),
        axis=1,
    )

    by_country = df.groupby("Country/Region").sum()
    dates = by_country.columns[2:]

    by_country.loc["Outside China", dates] = (
        by_country.sum().loc[dates] - by_country.loc["Mainland China", dates]
    )
    by_country = by_country.loc[:, dates].astype(int)
    dates = pd.to_datetime(dates)
    by_country.columns = dates
    bc = by_country.transpose()
    return bc


def make_contries_curves(
    df, counties=["Mainland China", "Outside China", "US", "UK"]
):

    p = plotting.figure(y_axis_type="log", x_axis_type="datetime")
    source = ColumnDataSource(df.loc[:, counties])
    legend_it = []
    for i, c in enumerate(counties):

        #     p.circle(x='index', y=c, source=source, legend=dict(value=c), color=colors[i])
        ln = p.line(
            x="index", y=c, source=source, color=colors[i], line_width=2
        )
        legend_it.append((c, [ln]))

    p.yaxis.formatter = FuncTickFormatter(code=code)
    legend = Legend(
        items=legend_it, location="center", orientation="horizontal"
    )
    legend.spacing = 17
    legend.click_policy = "hide"
    p.add_layout(legend, "above")

    label_opts = dict(
        x=df.index[-1], y=1, text_align="right", text_font_size="9pt"
    )

    caption = Label(
        text=f'Created by mrtommyb on {datetime.datetime.now().strftime("%b %d, %Y")}',
        **label_opts,
    )

    p.add_layout(caption, "below")

    script, div = components(p)
    embedfile = "_includes/infections_embed.html"
    with open(embedfile, "w") as ff:
        ff.write(div)
        ff.write(script)


def logistic_model(x, la, lb, lc):
    a, b, c = np.exp(la), np.exp(lb), np.exp(lc)
    return c / (1 + np.exp(-(x - b) / a))


def extrapolate_logistic(df, country="US", days_in_future=100, logy=True):
    dates = df.index
    y = df.loc[:, country].values
    x = (dates - np.datetime64(dates[0])).days

    p0 = np.log([2.3, 46, 2000])
    x0, cov = curve_fit(logistic_model, x, y, p0=p0, maxfev=10000)
    sds = np.sqrt(np.diag(cov))
    dts = np.arange(len(dates) + days_in_future)

    if logy:
        p = plotting.figure(y_axis_type="log", x_axis_type="datetime")
        p.yaxis.formatter = FuncTickFormatter(code=code)
    else:
        p = plotting.figure(y_axis_type="linear", x_axis_type="datetime")

    plt_dates = [
        dates[0] + datetime.timedelta(days=x) for x in range(0, dts[-1])
    ]
    p.line(
        plt_dates,
        logistic_model(dts, *x0),
        color=colors[0],
        line_width=2.0,
        line_dash="dashed",
    )
    ln = p.line(dates, logistic_model(x, *x0), color=colors[0], line_width=2)
    p.circle(x=dates, y=y, color=colors[0])
    legend_it = [(country, [ln])]
    legend = Legend(
        items=legend_it, location="top_right", orientation="horizontal"
    )
    legend.spacing = 17
    legend.click_policy = "hide"
    p.add_layout(legend, "above")

    label_opts = dict(
        x=plt_dates[-1],
        y=np.min(logistic_model(dts, *x0)),
        text_align="right",
        text_font_size="9pt",
    )

    caption = Label(
        text=f'Created by mrtommyb on {datetime.datetime.now().strftime("%b %d, %Y")}',
        **label_opts,
    )

    p.add_layout(caption, "below")

    script, div = components(p)
    embedfile = f"_includes/{country.replace(' ', '')}_infections_embed.html"
    with open(embedfile, "w") as ff:
        ff.write(div)
        ff.write(script)

    return [
        f'{(dates[0] + datetime.timedelta(days=np.exp(x0[1]))).strftime("%b %d, %Y")}',
        np.exp(x0[2]),
    ]


def run_mcmc(df, country="US", days_in_future=100, logy=True, totalPop=7e9):
    dates = df.index
    y = by_country.loc[:, country].values
    x = (dates - np.datetime64(dates[0])).days
    xplot = np.arange(x[-1] + days_in_future)

    p0 = np.log([2.3, 46, 2000])
    x0, cov = curve_fit(logistic_model, x, y, p0=p0, maxfev=10000)

    with pm.Model() as model:

        def logistic_cdf(x, la, lb, lc):
            a, b, c = tt.exp(la), tt.exp(lb), tt.exp(lc)
            return c / (1 + tt.exp(-(x - b) / a))

        loga = pm.Normal("loga", mu=tt.log(x0[0]), sd=2)
        logb = pm.Normal("logb", mu=tt.log(x0[1]), sd=5)

        popBound = pm.Bound(
            pm.Normal, upper=tt.log(totalPop), lower=tt.log(y[-1])
        )
        logc = popBound("logc", mu=tt.log(tt.min([x0[2], 0.1 * totalPop])), sd=25)
        logsd = pm.Normal("logsd", mu=2, sd=2)

        mod = logistic_cdf(x.values, loga, logb, logc)

        pm.Normal("obs", mu=mod, sd=tt.exp(logsd), observed=y)

        mod_eval = pm.Deterministic(
            "mod_eval", logistic_cdf(xplot, loga, logb, logc)
        )

        map_params = optimize()

        trace = pm.sample(
            draws=1000, tune=3000, chains=4, cores=2, start=map_params
        )

    q = np.percentile(trace["mod_eval"], q=[50, 90, 10], axis=0)

    if logy:
        p = plotting.figure(y_axis_type="log", x_axis_type="datetime")
        p.yaxis.formatter = FuncTickFormatter(code=code)
    else:
        p = plotting.figure(y_axis_type="linear", x_axis_type="datetime")

    # ln = p.line(
    #     [dates[0] + datetime.timedelta(days=x) for x in range(0, xplot[-1])],
    #     q[0],
    #     line_width=2,
    # )
    ln = p.line([dates[0] + datetime.timedelta(days=x) for x in range(0, xplot[-1])],
                np.mean(trace["mod_eval"], axis=0), line_width=2)
    p.line(
        [dates[0] + datetime.timedelta(days=x) for x in range(0, xplot[-1])],
        q[1],
        line_dash="dashed",
        line_width=1,
    )
    p.line(
        [dates[0] + datetime.timedelta(days=x) for x in range(0, xplot[-1])],
        q[2],
        line_dash="dashed",
        line_width=1,
    )
    p.circle(dates, y, color=colors[1])
    p.y_range=Range1d(1, 1.5*np.max(q[1]))
    p.yaxis.formatter = FuncTickFormatter(code=code)

    legend_it = [(country, [ln])]
    legend = Legend(
        items=legend_it, location="top_right", orientation="horizontal"
    )
    legend.spacing = 17
    legend.click_policy = "hide"
    p.add_layout(legend, "above")

    label_opts = dict(
        x=dates[-1],
        y=5,
        text_align="right",
        text_font_size="9pt",
    )

    caption = Label(
        text=f'Created by mrtommyb on {datetime.datetime.now().strftime("%b %d, %Y")}',
        **label_opts,
    )

    p.add_layout(caption, "below")

    script, div = components(p)
    embedfile = f"_includes/{country.replace(' ', '')}_infections_mcmc_embed.html"
    with open(embedfile, "w") as ff:
        ff.write(div)
        ff.write(script)


    return [
        f'{(dates[0] + datetime.timedelta(days=np.mean(np.exp(trace["logb"])))).strftime("%b %d, %Y")}',
        [np.mean(np.exp(trace['logc'])), *np.percentile(np.exp(trace['logc']), [90,10])],
    ]


def create_yaml(d, mcmc=False):
    yamlfile = "_data/data.yaml"
    with open(yamlfile, "w") as ff:
        ff.write(
            f'lastupdate: {datetime.datetime.now().strftime("%b %d, %Y")}\n'
        )
        ff.write("\n")
        ff.write("infections:\n")
        for k, v in d.items():
            if mcmc:
                if v[1][0] > 1000:
                    ff.write(f"        {k}: {v[1][0] / 1000:.1f} million [{v[1][2] / 1000:.1f} - {v[1][1] / 1000:.1f}]\n")
                else:
                    ff.write(f"        {k}: {v[1][0]:.1f} thousand [{v[1][2]:.1f} - {v[1][1]:.1f}]\n")
            else:
                if v[1] > 1000:
                    ff.write(f"        {k}: {v[1] / 1000:.1f} million\n")
                else:
                    ff.write(f"        {k}: {v[1]:.1f} thousand\n")

        ff.write("\n")
        ff.write("peakdate:\n")
        for k, v in d.items():
            ff.write(f"        {k}: {v[0]}\n")


if __name__ == "__main__":
    by_country = get_data()

    make_contries_curves(by_country)

    d = {}
    for country in [
        "Mainland China",
        "Outside China",
        "South Korea",
        "Italy",
        "US",
        "UK",
    ]:
        a, b = extrapolate_logistic(by_country, country)
        d[country.replace(" ", "")] = [a, b / 1000]
    create_yaml(d)

    d = {}
    pops = [1.3E9, 7.5E9-1.3E9, 51.5E6, 60E6, 327E6, 66E6]
    for i, country in enumerate([
        "Mainland China",
        "Outside China",
        "South Korea",
        "Italy",
        "US",
        "UK",
    ]):
        a, b = run_mcmc(by_country, country=country, totalPop=pops[i])
        d[country.replace(" ", "")] = [a, np.array(b) / 1000]

        create_yaml(d, mcmc=True)
