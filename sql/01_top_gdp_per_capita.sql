-- Query 1: Top 5 provinsi berdasarkan GDP/PDRB per kapita pada tahun terbaru.
-- Asumsi tabel DuckDB sudah terdaftar: fact_economics, dim_province, dim_year.

SELECT
    dp.province_name,
    dp.province_name_en,
    f.gdp_current_price,
    f.population,
    ROUND(f.gdp_per_capita, 2) AS gdp_per_capita_juta,
    dp.area_km2
FROM fact_economics f
JOIN dim_province dp ON f.province_id = dp.province_id
JOIN dim_year dy ON f.year_id = dy.year_id
WHERE dy.year = (SELECT MAX(year) FROM dim_year)
  AND f.gdp_per_capita IS NOT NULL
ORDER BY f.gdp_per_capita DESC
LIMIT 5;
