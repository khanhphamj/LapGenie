// ============================================================================
// Neo4j Database Schema Initialization Script for LapGenie Laptop Database
// ============================================================================
// This script creates ONLY the schema structure for laptop data including:
// - Unique constraints and indexes
// - No sample data - data will be imported from external sources
// ============================================================================

// Clear existing data (use with caution in production)
MATCH (n) DETACH DELETE n;

// ============================================================================
// CREATE CONSTRAINTS AND INDEXES
// ============================================================================

// Primary key constraints for all node types
CREATE CONSTRAINT laptop_product_id IF NOT EXISTS FOR (l:Laptop) REQUIRE l.productId IS UNIQUE;
CREATE CONSTRAINT brand_name IF NOT EXISTS FOR (b:Brand) REQUIRE b.name IS UNIQUE;
CREATE CONSTRAINT cpu_model_name IF NOT EXISTS FOR (c:CPU) REQUIRE c.modelName IS UNIQUE;
CREATE CONSTRAINT graphics_card_model_name IF NOT EXISTS FOR (g:GraphicsCard) REQUIRE g.modelName IS UNIQUE;
CREATE CONSTRAINT display_technology_name IF NOT EXISTS FOR (d:DisplayTechnology) REQUIRE d.name IS UNIQUE;
CREATE CONSTRAINT audio_technology_name IF NOT EXISTS FOR (a:AudioTechnology) REQUIRE a.name IS UNIQUE;
CREATE CONSTRAINT port_name IF NOT EXISTS FOR (p:Port) REQUIRE p.name IS UNIQUE;
CREATE CONSTRAINT wireless_technology_name IF NOT EXISTS FOR (w:WirelessTechnology) REQUIRE w.name IS UNIQUE;
CREATE CONSTRAINT feature_name IF NOT EXISTS FOR (f:Feature) REQUIRE f.name IS UNIQUE;
CREATE CONSTRAINT material_name IF NOT EXISTS FOR (m:Material) REQUIRE m.name IS UNIQUE;
CREATE CONSTRAINT price_segment_name IF NOT EXISTS FOR (ps:PriceSegment) REQUIRE ps.name IS UNIQUE;
CREATE CONSTRAINT price_tag_name IF NOT EXISTS FOR (pt:PriceTag) REQUIRE pt.name IS UNIQUE;

// Performance indexes for frequently queried properties
CREATE INDEX laptop_name_index IF NOT EXISTS FOR (l:Laptop) ON (l.name);
CREATE INDEX laptop_price_index IF NOT EXISTS FOR (l:Laptop) ON (l.currentPrice);
CREATE INDEX laptop_launch_year_index IF NOT EXISTS FOR (l:Laptop) ON (l.launchYear);
CREATE INDEX laptop_screen_size_index IF NOT EXISTS FOR (l:Laptop) ON (l.screenSizeInches);
CREATE INDEX laptop_ram_size_index IF NOT EXISTS FOR (l:Laptop) ON (l.ramSizeGB);
CREATE INDEX laptop_storage_capacity_index IF NOT EXISTS FOR (l:Laptop) ON (l.storageCapacityGB);

// Additional indexes for search optimization
CREATE INDEX cpu_cores_index IF NOT EXISTS FOR (c:CPU) ON (c.cores);
CREATE INDEX cpu_base_speed_index IF NOT EXISTS FOR (c:CPU) ON (c.baseSpeedGHz);
CREATE INDEX graphics_type_index IF NOT EXISTS FOR (g:GraphicsCard) ON (g.type);
CREATE INDEX graphics_vram_index IF NOT EXISTS FOR (g:GraphicsCard) ON (g.vramGB);

// ============================================================================
// SCHEMA VERIFICATION
// ============================================================================

// Show all constraints
SHOW CONSTRAINTS;

// Show all indexes
SHOW INDEXES;

// ============================================================================
// DATA IMPORT HELPER PROCEDURES
// ============================================================================

// Note: The following are example LOAD CSV queries for data import
// These are commented out and should be customized based on your actual data files

/*
// Example: Import Brands from CSV
LOAD CSV WITH HEADERS FROM 'file:///brands.csv' AS row
MERGE (b:Brand {name: row.name});

// Example: Import CPUs from CSV
LOAD CSV WITH HEADERS FROM 'file:///cpus.csv' AS row
MERGE (c:CPU {
    modelName: row.modelName,
    cores: toInteger(row.cores),
    threads: toInteger(row.threads),
    baseSpeedGHz: toFloat(row.baseSpeedGHz),
    maxSpeedGHz: row.maxSpeedGHz
});

// Example: Import Graphics Cards from CSV
LOAD CSV WITH HEADERS FROM 'file:///graphics_cards.csv' AS row
MERGE (g:GraphicsCard {
    modelName: row.modelName,
    type: row.type,
    vramGB: CASE WHEN row.vramGB IS NOT NULL THEN toInteger(row.vramGB) ELSE null END
});

// Example: Import Laptops from CSV
LOAD CSV WITH HEADERS FROM 'file:///laptops.csv' AS row
CREATE (l:Laptop {
    productId: row.productId,
    name: row.name,
    url: row.url,
    description: row.description,
    screenSizeInches: toFloat(row.screenSizeInches),
    screenResolutionText: row.screenResolutionText,
    screenRefreshRateHz: toInteger(row.screenRefreshRateHz),
    screenColorGamut: row.screenColorGamut,
    screenBrightnessNits: toInteger(row.screenBrightnessNits),
    ramSizeGB: toInteger(row.ramSizeGB),
    ramType: row.ramType,
    ramBusSpeedMHz: toInteger(row.ramBusSpeedMHz),
    ramMaxSupportNotes: row.ramMaxSupportNotes,
    storageCapacityGB: toInteger(row.storageCapacityGB),
    storageType: row.storageType,
    storageInterface: row.storageInterface,
    storageExpansionNotes: row.storageExpansionNotes,
    webcamInfo: row.webcamInfo,
    keyboardBacklight: row.keyboardBacklight,
    dimensionsAndWeight: row.dimensionsAndWeight,
    batteryInfo: row.batteryInfo,
    os: row.os,
    launchYear: toInteger(row.launchYear),
    currentPrice: toFloat(row.currentPrice),
    originalPriceText: row.originalPriceText,
    discountPercentageText: row.discountPercentageText
});