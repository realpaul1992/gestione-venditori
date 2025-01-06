-- MySQL dump 10.13  Distrib 9.1.0, for macos14 (arm64)
--
-- Host: localhost    Database: venditori_db
-- ------------------------------------------------------
-- Server version	9.1.0

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `settori`
--

DROP TABLE IF EXISTS `settori`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `settori` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nome` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `nome` (`nome`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `settori`
--

LOCK TABLES `settori` WRITE;
/*!40000 ALTER TABLE `settori` DISABLE KEYS */;
INSERT INTO `settori` VALUES (2,'Agricoltura e Alimentare'),(1,'Automotive'),(3,'Beni di Consumo');
/*!40000 ALTER TABLE `settori` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `venditori`
--

DROP TABLE IF EXISTS `venditori`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `venditori` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nome_cognome` varchar(255) NOT NULL,
  `email` varchar(255) NOT NULL,
  `telefono` varchar(20) DEFAULT NULL,
  `citta` varchar(100) DEFAULT NULL,
  `esperienza_vendita` int DEFAULT NULL,
  `anno_nascita` int DEFAULT NULL,
  `settore_esperienza` varchar(100) DEFAULT NULL,
  `partita_iva` enum('Sì','No') NOT NULL,
  `data_creazione` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `cv` varchar(255) DEFAULT NULL,
  `note` text,
  `agente_isenarco` text,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `venditori`
--

LOCK TABLES `venditori` WRITE;
/*!40000 ALTER TABLE `venditori` DISABLE KEYS */;
INSERT INTO `venditori` VALUES (1,'Mario Rossi','mario.rossi@example.com','1234567890','Milano',10,1901,'Beni di Consumo','Sì','2024-12-25 17:58:54','/Users/paolopatelli/Documents/Database venditori/cv_files/RecruitFlow_CO.MO.L.A.S.- COMMERCIO MOBILI LEGNAMI E AFFINI SIENA - S.R.L.pdf','Paolo locodwwww','No'),(7,'Luca','luca@gmail.com','333','Abano Terme',19,1900,'Agricoltura e Alimentare','Sì','2024-12-28 10:01:22',NULL,NULL,'Sì');
/*!40000 ALTER TABLE `venditori` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2024-12-30  8:58:21
