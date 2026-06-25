-- Query 6: Perbandingan kepadatan penduduk dan GDP/PDRB per kapita.
-- Asumsi tabel DuckDB sudah terdaftar: fact_economics, dim_province, dim_year.

SELECT
    dp.province_name,
    f.population,
    dp.area_km2,
    ROUND(CAST(f.population AS DOUBLE) / NULLIF(dp.area_km2, 0), 2) AS population_density,
    ROUND(f.gdp_per_capita, 2) AS gdp_per_capita_juta,
    f.gdp_current_price AS total_gdp_miliar
FROM fact_economics f
JOIN dim_province dp ON f.province_id = dp.province_id
JOIN dim_year dy ON f.year_id = dy.year_id
WHERE dy.year = (SELECT MAX(year) FROM dim_year)
  AND dp.area_km2 > 0
  AND f.population > 0
ORDER BY population_density DESC
LIMIT 10;
