-- Query 3: Pertumbuhan PDRB year-over-year untuk provinsi di Pulau Jawa.
-- Asumsi tabel DuckDB sudah terdaftar: fact_economics, dim_province, dim_year.

SELECT
    dp.province_name,
    dy.year,
    f.gdp_current_price,
    LAG(f.gdp_current_price) OVER (
        PARTITION BY dp.province_name
        ORDER BY dy.year
    ) AS prev_year_gdp,
    ROUND(
        (
            (f.gdp_current_price - LAG(f.gdp_current_price) OVER (
                PARTITION BY dp.province_name
                ORDER BY dy.year
            ))
            / NULLIF(LAG(f.gdp_current_price) OVER (
                PARTITION BY dp.province_name
                ORDER BY dy.year
            ), 0)
        ) * 100,
        2
    ) AS growth_rate_pct
FROM fact_economics f
JOIN dim_province dp ON f.province_id = dp.province_id
JOIN dim_year dy ON f.year_id = dy.year_id
WHERE dp.province_name IN ('Jakarta', 'DKI Jakarta', 'Jawa Barat', 'Jawa Tengah', 'Jawa Timur', 'Banten', 'Yogyakarta', 'DI Yogyakarta')
ORDER BY dp.province_name, dy.year;
