# Power Query M Scripts

These M scripts replicate the Python ETL transforms directly inside Power BI.
Paste each into Power Query Editor → Advanced Editor.

---

## 1. Load & Clean Opportunities

```m
let
    Source = Csv.Document(
        File.Contents("C:\YourPath\data\exports\win_rate.csv"),
        [Delimiter=",", Columns=7, Encoding=65001, QuoteStyle=QuoteStyle.None]
    ),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Types" = Table.TransformColumnTypes(#"Promoted Headers", {
        {"total_closed",  Int64.Type},
        {"won",           Int64.Type},
        {"win_rate",      type number},
        {"month_year",    type text},
        {"rep_name",      type text},
        {"region",        type text},
        {"territory",     type text}
    }),
    #"Added Win Rate %" = Table.AddColumn(
        #"Changed Types", "Win Rate %",
        each [win_rate] * 100,
        type number
    ),
    #"Added Month Date" = Table.AddColumn(
        #"Added Win Rate %", "Month Date",
        each Date.FromText([month_year] & "-01"),
        type date
    ),
    #"Sorted by Month" = Table.Sort(
        #"Added Month Date",
        {{"Month Date", Order.Descending}}
    )
in
    #"Sorted by Month"
```

---

## 2. Load Revenue & Add MoM Variance

```m
let
    Source = Csv.Document(
        File.Contents("C:\YourPath\data\exports\mom_variance.csv"),
        [Delimiter=",", Columns=5, Encoding=65001]
    ),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Types" = Table.TransformColumnTypes(#"Promoted Headers", {
        {"month_year",        type text},
        {"current_revenue",   type number},
        {"previous_revenue",  type number},
        {"variance",          type number},
        {"variance_pct",      type number}
    }),
    #"Added Month Date" = Table.AddColumn(
        #"Changed Types", "Month Date",
        each Date.FromText([month_year] & "-01"),
        type date
    ),
    #"Added Variance Flag" = Table.AddColumn(
        #"Added Month Date", "Variance Direction",
        each if [variance] >= 0 then "Positive" else "Negative",
        type text
    ),
    #"Sorted Ascending" = Table.Sort(
        #"Added Variance Flag",
        {{"Month Date", Order.Ascending}}
    )
in
    #"Sorted Ascending"
```

---

## 3. Load Quota Attainment & Band

```m
let
    Source = Csv.Document(
        File.Contents("C:\YourPath\data\exports\quota_attainment.csv"),
        [Delimiter=",", Columns=7, Encoding=65001]
    ),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Types" = Table.TransformColumnTypes(#"Promoted Headers", {
        {"actual_revenue",    type number},
        {"quota_amount",      type number},
        {"quota_attainment",  type number}
    }),
    #"Added Attainment Band" = Table.AddColumn(
        #"Changed Types", "Attainment Band",
        each if [quota_attainment] >= 1.2 then "Exceeds (>120%)"
             else if [quota_attainment] >= 1.0 then "On Track (100-120%)"
             else if [quota_attainment] >= 0.8 then "Near Target (80-100%)"
             else if [quota_attainment] >= 0.5 then "At Risk (50-80%)"
             else "Critical (<50%)",
        type text
    ),
    #"Added Month Date" = Table.AddColumn(
        #"Added Attainment Band", "Month Date",
        each Date.FromText([month_year] & "-01"),
        type date
    )
in
    #"Added Month Date"
```

---

## 4. Date Dimension Table

```m
let
    StartDate = #date(2023, 1, 1),
    EndDate   = #date(2024, 12, 31),
    DayCount  = Duration.Days(EndDate - StartDate) + 1,
    DateList  = List.Dates(StartDate, DayCount, #duration(1,0,0,0)),
    TableFromList = Table.FromList(DateList, Splitter.SplitByNothing(), {"Date"}),
    #"Changed Type" = Table.TransformColumnTypes(TableFromList, {{"Date", type date}}),
    #"Added Year" = Table.AddColumn(#"Changed Type",     "Year",       each Date.Year([Date]),          Int64.Type),
    #"Added Quarter" = Table.AddColumn(#"Added Year",    "Quarter",    each Date.QuarterOfYear([Date]),  Int64.Type),
    #"Added Month" = Table.AddColumn(#"Added Quarter",   "Month",      each Date.Month([Date]),          Int64.Type),
    #"Added Month Name" = Table.AddColumn(#"Added Month","Month Name", each Date.ToText([Date], "MMMM"), type text),
    #"Added Week" = Table.AddColumn(#"Added Month Name", "Week",       each Date.WeekOfYear([Date]),     Int64.Type),
    #"Added DOW" = Table.AddColumn(#"Added Week",        "Day of Week",each Date.DayOfWeek([Date]),      Int64.Type),
    #"Added IsWeekday" = Table.AddColumn(#"Added DOW",   "Is Weekday", each [Day of Week] < 5,           type logical),
    #"Added MonthYear" = Table.AddColumn(#"Added IsWeekday","Month Year",
        each Text.PadStart(Text.From([Month]),2,"0") & "/" & Text.From([Year]),
        type text)
in
    #"Added MonthYear"
```

---

## 5. Merge Rep Dimension Into Revenue

```m
let
    Revenue = #"fact_revenue",   -- reference your revenue query
    Reps    = #"dim_reps",       -- reference your reps query
    Merged  = Table.NestedJoin(
        Revenue, {"rep_id"},
        Reps,    {"rep_id"},
        "RepData", JoinKind.LeftOuter
    ),
    Expanded = Table.ExpandTableColumn(
        Merged, "RepData",
        {"rep_name", "region", "territory"},
        {"rep_name", "region", "territory"}
    )
in
    Expanded
```
