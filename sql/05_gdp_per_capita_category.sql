-- Query 5: Kategori provinsi di atas atau di bawah rata-rata GDP/PDRB per kapita nasional.
-- Asumsi tabel DuckDB sudah terdaftar: fact_economics, dim_year.

WITH national_avg AS (
    SELECT AVG(f.gdp_per_capita) AS avg_gdp_pc
    FROM fact_economics f
    JOIN dim_year dy ON f.year_id = dy.year_id
    WHERE dy.year = (SELECT MAX(year) FROM dim_year)
      AND f.gdp_per_capita IS NOT NULL
)
SELECT
    CASE
        WHEN f.gdp_per_capita >= na.avg_gdp_pc THEN 'Di Atas Rata-rata'
        ELSE 'Di Bawah Rata-rata'
    END AS kategori,
    COUNT(*) AS jumlah_provinsi,
    ROUND(AVG(f.gdp_per_capita), 2) AS avg_gdp_per_capita,
    ROUND(MIN(f.gdp_per_capita), 2) AS min_gdp_per_capita,
    ROUND(MAX(f.gdp_per_capita), 2) AS max_gdp_per_capita,
    SUM(f.population) AS total_populasi
FROM fact_economics f
JOIN dim_year dy ON f.year_id = dy.year_id
CROSS JOIN national_avg na
WHERE dy.year = (SELECT MAX(year) FROM dim_year)
  AND f.gdp_per_capita IS NOT NULL
GROUP BY kategori;
