-- Query 2: Rata-rata PDRB dan GDP/PDRB per kapita berdasarkan kelompok pulau.
-- Asumsi tabel DuckDB sudah terdaftar: fact_economics, dim_province, dim_year.

SELECT
    CASE
        WHEN dp.province_name IN ('Jakarta', 'DKI Jakarta', 'Jawa Barat', 'Jawa Tengah', 'Yogyakarta', 'DI Yogyakarta', 'Jawa Timur', 'Banten') THEN 'Jawa'
        WHEN dp.province_name IN ('Aceh', 'Sumatera Utara', 'Sumatera Barat', 'Riau', 'Jambi', 'Sumatera Selatan', 'Bengkulu', 'Lampung', 'Kepulauan Bangka Belitung', 'Kepulauan Riau') THEN 'Sumatera'
        WHEN dp.province_name LIKE '%Kalimantan%' THEN 'Kalimantan'
        WHEN dp.province_name LIKE '%Sulawesi%' OR dp.province_name = 'Gorontalo' THEN 'Sulawesi'
        WHEN dp.province_name LIKE '%Papua%' THEN 'Papua'
        WHEN dp.province_name IN ('Bali', 'Nusa Tenggara Barat', 'Nusa Tenggara Timur') THEN 'Bali & Nusa Tenggara'
        WHEN dp.province_name IN ('Maluku', 'Maluku Utara') THEN 'Maluku'
        ELSE 'Lainnya'
    END AS island_group,
    COUNT(*) AS province_count,
    ROUND(AVG(f.gdp_current_price), 2) AS avg_gdp_miliar,
    SUM(f.population) AS total_population,
    ROUND(AVG(f.gdp_per_capita), 2) AS avg_gdp_per_capita
FROM fact_economics f
JOIN dim_province dp ON f.province_id = dp.province_id
JOIN dim_year dy ON f.year_id = dy.year_id
WHERE dy.year = (SELECT MAX(year) FROM dim_year)
GROUP BY island_group
ORDER BY avg_gdp_miliar DESC;
