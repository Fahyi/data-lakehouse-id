-- Query 4: Tren populasi nasional dan rata-rata GDP/PDRB per kapita.
-- Asumsi tabel DuckDB sudah terdaftar: fact_economics, dim_year.

SELECT
    dy.year,
    SUM(f.population) AS total_national_population,
    COUNT(DISTINCT f.province_id) AS province_count,
    ROUND(AVG(f.gdp_per_capita), 2) AS avg_gdp_per_capita,
    ROUND(SUM(f.gdp_current_price), 2) AS total_national_gdp
FROM fact_economics f
JOIN dim_year dy ON f.year_id = dy.year_id
WHERE f.population > 0
GROUP BY dy.year
ORDER BY dy.year;
