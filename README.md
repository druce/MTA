# MTA
chart MTA subway entries

![NYC Subway entries](chart.png)

# A data stack-in-a-box?

You might say, it's not big data if it fits on single box like my laptop. One definition of big data used to be, data that is too big to be handled on a single box.

But times have changed. You can fit a lot on a single box. I have a 2019 Intel MacBook Pro with 32GB of RAM. So with the right stack, I can effectively analyze maybe 20 years of MTA data down to individual turnstiles. Which is 'pretty big' data.

Are clusters decreasingly relevant? Modern CPU architectures like [Zen](https://en.wikipedia.org/wiki/Zen_4) change many things, if not everything. When Google first came out, the part that truly blew my mind was not just that it had an order-of-magnitude bigger index and better relevance. But when you ran a search, the results gave not just a URL, but *the excerpt on the page* that matched your search. Google was *caching the text of the entire Web in RAM*. A cluster farmed out your search to dozens of PCs (really some circuit boards zip-tied together), each of which kept a shard of the index in RAM, got the top-ranking result from each shard, also looked up the relevant page and located the relevant excerpt, then sorted all this and assembled it into a results page. In a fraction of a second. Google clusters were a radical new computing paradigm that expanded what was possible. 

Today the pendulum has swung the other way. We almost always run multiple virtual servers on a single physical server. It is *cheaper* to run a giant [AMD Epyc box](https://aws.amazon.com/blogs/aws/new-amazon-ec2-c6a-instances-powered-by-3rd-gen-amd-epyc-processors-for-compute-intensive-workloads/) with 192 cores and 384GB of RAM than equivalent compute on individual servers. You can even rent an [8-socket Intel box with 24 TB of RAM](https://aws.amazon.com/ec2/instance-types/high-memory/)! Big data, defined as tabular data too big to fit on a single box in RAM, hardly even exists outside Big Tech. Machines have grown even faster than tabular datasets.[^1]

Giant CPUs and SoCs change the way software is built. For super high performance light microservices you may want to [pin each thread to a core](https://twitter.com/alexxubyte/status/1588203762945884160), keep everything in CPU cache, and never context-switch. As Moore's law flies into the sunset, expanding the envelope is more about giant dies for systems-on-a-chip (SoCs). That's [the secret](https://debugger.medium.com/why-is-apples-m1-chip-so-fast-3262b158cba2) of Apple's M1, it's not just a CPU, it also puts memory, I/O, GPU on a single chip for massive bandwidth. 

If you can fit the data on one box, the juice may not be worth the squeeze to make a cluster, when you properly take advantage of a big box's memory, many cores, and massive bus bandwidth. Vertical is the new horizontal. 

Hence, the data stack-in-a-box. 

# Components 

We can divide what the data stack-in-a-box will do into 6 tasks:

1. Data storage to manage the data and let us query it and aggregate it efficiently, taking full advantage of all the RAM and cores: a DBMS, data warehouse, data lake, lakehouse etc.

2. Tools to fetch data and ingest from REST APIs, CSVs, Parquet etc. via standard protocols. Built-in schemas for e.g. Zoom or Salesforce data and APIs would be nice.

3. A scheduler / orchestrator to check for new data and trigger jobs when needed: maybe on a schedule, maybe monitoring a local directory, maybe polling a remote directory, maybe receiving emails or other signals.

4. Tools to manage dependency graphs ([DAGs](https://en.wikipedia.org/wiki/Directed_acyclic_graph)) to trigger jobs like DB transformation / build, data quality, ML training, inference, notifications downstream when jobs succeed or fail.

5. Tools to munge data, extract, load, and transform (ELT).

6. Front end frameworks to create dataviz, reports, dashboards and end-user apps.

This is just one way to slice the salami. It might be simpler to break down into data warehouse, ELT, BI/front end. In practice especially the middle 2-5 can overlap but there are often multiple products. There are also [additional pieces](https://i.redd.it/pdnuk1r0yjf71.jpg), like [monitoring pipelines](https://www.acceldata.io/article/what-is-data-pipeline-monitoring) in production, [data quality](https://greatexpectations.io/), [data governance](https://www.collibra.com/us/en/products/data-governance). You can go [pretty deep](https://mattturck.wpenginepowered.com/wp-content/uploads/2021/12/2021-MAD-Landscape-v3.pdf). But if you've handled these concerns, you have a pretty good start.

An aside: Why ELT and not ETL? Earlier online analytic processing (OLAP) manifestations processed data into [cubes](https://en.wikipedia.org/wiki/OLAP_cube), sort of like a spreadsheet with a pivot table within a database, to batch pre-process aggregations and enable real-time drilldowns. Modern data stacks just keep data in raw form (or close to it) and leverage parallel processing to transform on the fly. We give each core a shard of the data in RAM. Then each node can do its part of aggregations and drilldowns and send the results to a controller for final compilations, [MapReduce](https://en.wikipedia.org/wiki/MapReduce) paradigm style. In contrast to a client/server paradigm which moves data around disks and network, we marry each slice of data with nearby dedicated compute. Thus ELT in contrast to old-school ETL. In practice, however, we usually end up with ETLT: extract; clean up a little; load to our data warehouse in a clean, but unaggregated form; do major aggregation on the fly without needing to determine up front what dimensions we might want to aggregate as in an OLAP cube.

How could we build a basic [modern data stack](https://www.getdbt.com/blog/future-of-the-modern-data-stack/) with [MTA turnstile source data](https://data.ny.gov/Transportation/Turnstile-Usage-Data-2020/py8k-a8wg) to power dashboards like [this](https://toddwschneider.com/dashboards/nyc-subway-turnstiles/) or [this](https://www.subwayridership.nyc/)?

One way is an enterprise-ish 'on-prem' approach (but typically in private or public cloud these days):
- Storage + compute: Spark cluster 
- Pipeline management: Airflow, dbt, Fivetran, Stitch, Airbyte 
- Dataviz: PowerBI, Tableau, Superset
- Apps: Django web apps, Appsmith low-code

Another approach is 'cloud-native', using pay-as-you-go SaaS cloud services connected over public Inernet:
- Storage + compute: Cloud lakehouse like Snowflake or Databricks hosted Spark
- Cloud pipeline management: Astronomer hosted Airflow, Prefect, Dagster Cloud, dbt Cloud
- Cloud analytics service, Tableau Cloud, PowerBI SaaS, Preset hosted Superset
- Retool, Appsmith Cloud, with hosted Postgres to deliver end-user apps

With a cloud-native stack, SMBs can run their business more or less completely on SaaS services like Salesforce, Square, NetSuite, Workday, Mailchimp, Twilio, Zoom. Who needs devs and system admins and MSPs? When you want to build a workflow app, for instance to manage a big conference, create some Zoom meetings, send some emails, texts, Slack/Discord messages, and get paid, build a front end in Retool to talk to all those SaaS services. 

# Implementation

But I'm not going to build any of these heavyweight solutions, I want a lightweight stack to pull 'pretty large' data, run an analysis, and display a dashboard on my MacBook or in a container, for a data stack-in-a-box. Tech we will leverage:

- [Duckdb](https://duckdb.org/): like SQLlite, but for column-oriented data. It's a lightweight module that does high-performance multithreaded aggregation using SQL. [Columnar databases are faster for OLAP than row-oriented OLTP databases like Postgres](https://loonytek.com/2017/05/04/why-analytic-workloads-are-faster-on-columnar-databases/).[^2] When we have e.g. millions of rows of e.g. double-digit columns, we usually get orders of magnitude improvement in size/speed using a columnar format like Parquet vs. CSV with binary storage and compression.

- [dbt](https://www.getdbt.com/blog/future-of-the-modern-data-stack/): the database build tool. From your data warehouse's perspective, dbt is simply a SQL client. But when you write your SQL scripts within the dbt framework, you get almost for free: DAG workflow; logging; self-documentation of every table's provenance; parameterized SQL templates for modularity and re-use, and the ability to point any script to dev / test / production environments. 

- [Superset](https://superset.apache.org): an open source version of Tableau or PowerBI to run a dashboard.

- [Meltano](https://meltano.com): a CLI to manage data pipelines, that can ingest data via [Singer taps](https://www.singer.io/#taps) and [Airbyte connectors](https://airbyte.com/connectors). It's the closest thing I've seen to an API of all APIs.

This works pretty well ([code here](https://github.com/druce/MTA)). It's an order of magnitude faster than raw pandas on 'pretty big' data. It will analyze data fast, and it's a nice way to understand how the data sausage is made. It's awesomely cool, if you grew up in a world where Google didn't exist, to be able to compute Google-style on your laptop or a $20 Hetzner or AWS box. It's close to production-ready when the time comes to move from your laptop to 'real' enterprise infrastructure, whether SaaS or 'on-prem'. If you sub Spark for DuckDB, this data-warehouse-in-a-box starts is a decent starting point for an enterprise stack.

But of course, if you are a normie business, just get Databricks (hosted Spark) or Snowflake (SQL data warehouse).  No offense to others but those are the dominant SaaS solutions. There are [a lot of ways](https://www.moderndatastack.xyz/stacks) to skin this cat. This dude even has a ['post-modern' data stack](https://blog.devgenius.io/modern-data-stack-demo-5d75dcdfba50). 

At this point, rolling your own modern data stack is for teams with scale. Or penniless startups and hobbyists who don't want to pay for SaaS services. Which is probably not most teams. Regardless here is our own small environment for a data app.


