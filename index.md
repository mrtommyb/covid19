# Current status of infections

{% include infections_embed.html %}
This shows the number of confirmed infections reported by the Johns Hopkins University [Center for Systems Science and Engineering (JHU CSSE)](https://systems.jhu.edu/) for a few countries I thought interesting. They have some [great visualizations](https://www.arcgis.com/apps/opsdashboard/index.html#/bda7594740fd40299423467b48e9ecf6), you should check it out. Data comes from their [github repo](https://github.com/CSSEGISandData/COVID-19) and is updated every day.

# Extrapolations of cumulative infections for various countries

I took the observed number of confirmed COVID-19 cases and fit a logistic distribution to the data. This is a sigmoid shape and so allows for exponential grown that slowly 

## US infection extrapolation from a model

{% include US_infections_mcmc_embed.html %}

As of {{site.data.data.lastupdate}}, the model predicts that US infection rate will reach its **peak on {{site.data.data.peakdate.US}}** and a total of **{{site.data.data.infections.US}} people will have been infected** .

## UK infection extrapolation from a model

{% include UK_infections_mcmc_embed.html %}

As of {{site.data.data.lastupdate}}, the model predicts that UK infection rate will reach its **peak on {{site.data.data.peakdate.UK}}** and a total of **{{site.data.data.infections.UK}} people will be infected**.

## China infection extrapolation from a model

{% include MainlandChina_infections_mcmc_embed.html %}

As of {{site.data.data.lastupdate}}, the model predicts that China infection rate reached its **peak on {{site.data.data.peakdate.MainlandChina}}** and a total of **{{site.data.data.infections.MainlandChina}} people will be infected**.


<!-- # Outside China infection extrapolation from a model

{% include OutsideChina_infections_mcmc_embed.html %}

As of {{site.data.data.lastupdate}}, the model predicts that for all counties other than China the infection rate will reach its peak on {{site.data.data.peakdate.OutsideChina}} and **{{site.data.data.infections.OutsideChina}} people will be infected**. -->

## South Korea infection extrapolation from a model

{% include SouthKorea_infections_mcmc_embed.html %}

As of {{site.data.data.lastupdate}}, the model predicts that South Korea infection rate will reach its **peak on {{site.data.data.peakdate.SouthKorea}}** and a total of **{{site.data.data.infections.SouthKorea}} people will be infected**.

## Italy infection extrapolation from a model

{% include Italy_infections_mcmc_embed.html %}

As of {{site.data.data.lastupdate}}, the model predicts that Italy infection rate will reach its **peak on {{site.data.data.peakdate.Italy}}** and a total of **{{site.data.data.infections.Italy}} people will be infected**.


# Thanks (i.e. who I took ideas and code from)
I got the idea for this site from a reddit post.