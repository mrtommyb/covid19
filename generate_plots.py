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

confirmed_url = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv"
deaths_url = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv"

# colorblind friendly palette from https://personal.sron.nl/~pault/
# other ideas: https://thenode.biologists.com/data-visualization-with-flying-colors/research/
# colors = [
#     "#228833",
#     "#ee6677",
#     "#4477aa",
#     "#aa3377",
#     "#ccbb44",
#     "#aaaaaa",
#     "#66ccee",
# ]
colors = [
    "#1abc9c",
    "#c0392b",
    "#2ecc71",
    "#3498db",
    "#9b59b6",
    "#34495e",
    "#16a085",
    "#27ae60",
    "#2980b9",
    "#8e44ad",
    "#2c3e50",
    "#f1c40f",
    "#e67e22",
    "#e74c3c",
    "#95a5a6",
    "#f39c12",
    "#d35400",
    "#7f8c8d",
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
        by_country.sum().loc[dates] - by_country.loc["China", dates]
    )
    by_country = by_country.loc[:, dates].astype(int)
    dates = pd.to_datetime(dates)
    by_country.columns = dates
    bc = by_country.transpose()
    bc = bc.rename(
        columns={
            # "Iran (Islamic Republic of)": "Iran",
            "Korea, South": "South Korea"
        }
    )
    return bc


def make_contries_curves(
    df, countries=["Mainland China", "Outside China", "US", "UK"]
):

    p = plotting.figure(y_axis_type="log", x_axis_type="datetime")
    source = ColumnDataSource(df.loc[:, countries])
    legend_it = []
    for i, c in enumerate(countries):

        #     p.circle(x='index', y=c, source=source, legend=dict(value=c), color=colors[i])
        ln = p.line(
            x="index", y=c, source=source, color=colors[i], line_width=2
        )
        legend_it.append((c, [ln]))

    p.yaxis.formatter = FuncTickFormatter(code=code)
    legend = Legend(
        items=legend_it, location="center", orientation="horizontal"
    )
    legend.spacing = 8
    legend.click_policy = "hide"
    p.add_layout(legend, "above")

    label_opts = dict(
        x=df.index[-1], y=1, text_align="right", text_font_size="7pt"
    )

    caption = Label(
        text=f'Created by Tom Barclay on {datetime.datetime.now().strftime("%b %d, %Y")}',
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
        p = plotting.figure(y_axis_type="log", x_axis_type="datetime")

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
        text=f'Created by Tom Barclay on {datetime.datetime.now().strftime("%b %d, %Y")}',
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


def run_mcmc(
    df,
    country="US",
    days_in_future=50,
    logy=True,
    totalPop=7e9,
    tune=5000,
    draws=1200,
):
    dates = df.index
    y = by_country.loc[:, country].values
    x = (dates - np.datetime64(dates[0])).days
    xplot = np.arange(x[-1] + days_in_future)

    p0 = np.log([2.3, 46, 2000])
    x0, cov = curve_fit(logistic_model, x, y, p0=p0, maxfev=10000)

    with pm.Model() as model:

        def logistic_cdf(x, la, lb, lc):
            a, b, c = la, tt.exp(lb), tt.exp(lc)
            return c / (1 + tt.exp(-(x - b) / a))

        # growthBound = pm.Bound(pm.Normal, lower=0)
        # loga = growthBound("loga", mu=tt.log(5), sd=3)
        growthBound = pm.Bound(pm.Gamma, lower=1)
        a = growthBound("loga", alpha=3.5, beta=1)

        logb = pm.Normal("logb", mu=tt.log(150), sd=3)

        popBound = pm.Bound(
            pm.Normal, upper=tt.log(totalPop), lower=tt.log(y[-1])
        )
        logc = popBound("logc", mu=np.log(0.1 * totalPop), sd=5)

        # switching to an InvGamma prior on sd, cos its the conjugate
        # prior of the normal distrbution with unknown sd

        # logsd = pm.Normal("logsd", mu=2, sd=2)
        mask = y > 50
        sd = pm.InverseGamma(
            "logsd",
            mu=np.std(y[mask] / x[mask]),
            sd=np.std(y[mask] / x[mask]) / len(x[mask]),
        )

        mod = logistic_cdf(x.values[mask], a, logb, logc)

        # pm.Normal("obs", mu=mod, sd=sd, observed=y[mask])
        # move to Negative Binomial
        pm.obs = pm.NegativeBinomial('obs', mod, sd, observed=y[mask])

        mod_eval = pm.Deterministic(
            "mod_eval", logistic_cdf(xplot, a, logb, logc)
        )

        map_params = optimize()

        trace = pm.sample(
            draws=draws,
            tune=tune,
            chains=2,
            cores=2,
            start=map_params,
            target_accept=0.9,
            progressbar=False,
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
    ln = p.line(
        [dates[0] + datetime.timedelta(days=x) for x in range(0, xplot[-1])],
        np.mean(trace["mod_eval"], axis=0),
        line_width=2,
    )
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
    p.y_range = Range1d(10, 1.2 * np.max(q[1]))
    p.yaxis.formatter = FuncTickFormatter(code=code)

    legend_it = [(country, [ln])]
    legend = Legend(
        items=legend_it, location="top_right", orientation="horizontal"
    )
    legend.spacing = 17
    legend.click_policy = "hide"
    p.add_layout(legend, "above")

    label_opts = dict(
        x=dates[0] + datetime.timedelta(days=int(xplot[-1])),
        y=np.max(q[1]) * 1.1,
        text_align="right",
        text_font_size="9pt",
    )

    caption = Label(
        text=f'Created by Tom Barclay on {datetime.datetime.now().strftime("%b %d, %Y")}',
        **label_opts,
    )

    p.add_layout(caption, "below")

    script, div = components(p)
    embedfile = (
        f"_includes/{country.replace(' ', '')}_infections_mcmc_embed.html"
    )
    with open(embedfile, "w") as ff:
        ff.write(div)
        ff.write(script)

    return [
        f'{(dates[0] + datetime.timedelta(days=np.mean(np.exp(trace["logb"])))).strftime("%b %d, %Y")}',
        [
            np.mean(np.exp(trace["logc"])),
            *np.percentile(np.exp(trace["logc"]), [90, 10]),
        ],
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
                if v[1][0] > 10000:
                    ff.write(
                        f"        {k}: {v[1][0] / 1000:.2f} [{v[1][2] / 1000:.2f} - {v[1][1] / 1000:.2f}] million\n"
                    )
                else:
                    ff.write(
                        f"        {k}: {v[1][0]:.2f} [{v[1][2]:.2f} - {v[1][1]:.2f}] thousand\n"
                    )
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

    # bad data on March 12
    by_country = by_country.drop(pd.Timestamp("2020-03-12"))

    # let's list all countries with at least as many cases than uk
    # as of writing these are
    # 'France', 'Germany', 'Iran', 'Italy', 'Japan', 'Mainland China',
    #    'Netherlands', 'Others', 'South Korea', 'Spain', 'Switzerland',
    #    'UK', 'US',

    do_these_countries = list(
        by_country.loc[
            :, by_country.iloc[-1] >= by_country.iloc[-1]["United Kingdom"]
        ].columns.values
    )
    # do_these_countries.remove("Others")
    # do_these_countries.remove("Cruise Ship")

    do_these = [
        "Iran",
        "Italy",
        "Japan",
        "China",
        "South Korea",
        "United Kingdom",
        "US",
    ]
    make_contries_curves(by_country, countries=do_these)

    d = {}
    for country in do_these_countries:
        a, b = extrapolate_logistic(by_country, country)
        d[country.replace(" ", "")] = [a, b / 1000]
    create_yaml(d)

    d = {}
    pops = [
        1.3e9,
        # 7.5e9 - 1.3e9,
        51.5e6,
        60e6,
        327e6,
        66e6,
        66.99e6,
        82.79e6,
        81.16e6,
        126.8e6,
        17.18e6,
        46.66e6,
        8.57e6,
    ]
    for i, country in enumerate(
        [
            "China",
            # "Outside China",
            "South Korea",
            "Italy",
            "US",
            "United Kingdom",
            "France",
            "Germany",
            "Iran",
            "Japan",
            "Netherlands",
            "Spain",
            "Switzerland",
        ]
    ):
        a, b = run_mcmc(
            by_country,
            country=country,
            totalPop=pops[i],
            logy=True,
            tune=5000,
            draws=1200,
        )
        d[country.replace(" ", "")] = [a, np.array(b) / 1000]

    create_yaml(d, mcmc=True)
