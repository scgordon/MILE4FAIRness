<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:saxon="http://saxon.sf.net/" version="2.0">
  
  <xsl:param name="recordSetPath"/>
  <xsl:param name="fileNamePattern" select="'*.xml'"/>
  <xsl:param name="showValues" select="1"/>
  <xsl:param name="showFilename" select="1"/>
  <xsl:param name="showCollectionName" select="1"/>
  <xsl:param name="delimiter" select="','"/>
  <xsl:output method="text"/>
  <xsl:strip-space elements="*"/>
  <xsl:template match="/">
    <xsl:if test="$showCollectionName">
      <xsl:text>Collection</xsl:text>
      <xsl:value-of select="$delimiter"/>
    </xsl:if>
    <xsl:if test="$showFilename">
      <xsl:text>Record</xsl:text>
      <xsl:value-of select="$delimiter"/>
    </xsl:if>
    <xsl:text>XPath</xsl:text>
    <xsl:if test="$showValues">
      <xsl:value-of select="$delimiter"/>
      <xsl:text>Content</xsl:text>
    </xsl:if>
    <xsl:text>&#xa;</xsl:text>
    <xsl:for-each select="tokenize($fileNamePattern, ' ')">
      <xsl:variable name="xmlFilesSelect" select="concat($recordSetPath, '?select=', string(.))"/>
      <xsl:for-each select="collection(iri-to-uri($xmlFilesSelect))">
        <!-- Determine Collection Name using the standard directory structure collection/dialect/xml/metadataRecords.
          This option is only useful in the standard collection analysis scenario.
        -->
        <!--<xsl:variable name="collectionName">
          <xsl:for-each select="tokenize(document-uri(.), '/')">
            <xsl:if test="position() = last() - 3">
              <xsl:value-of select="."/>
            </xsl:if>
          </xsl:for-each>
        </xsl:variable>-->
        <xsl:apply-templates>
          <xsl:with-param name="collectionName" select="tokenize(document-uri(.), '/')[last() - 1]"/>
          <xsl:with-param name="fileName" select="tokenize(document-uri(.), '/')[last()]"/>
        </xsl:apply-templates>
      </xsl:for-each>
    </xsl:for-each>
  </xsl:template>
  <xsl:template match="node()">
    <xsl:param name="fileName"/>
    <xsl:param name="collectionName"></xsl:param>
    
    <xsl:if test="not(normalize-space(text()[1]) = '')">
      <xsl:if test="$showCollectionName">
        <xsl:value-of select="$collectionName"/>
        <xsl:value-of select="$delimiter"/>
      </xsl:if>
      <xsl:if test="$showFilename">
        <xsl:value-of select="$fileName"/>
        <xsl:value-of select="$delimiter"/>
      </xsl:if>
      <xsl:value-of select="replace(saxon:path(), '\[\d*\]', '')"/>
      <xsl:if test="$showValues">
        <xsl:value-of select="$delimiter"/>
        <xsl:text>"</xsl:text>
        <xsl:value-of select="replace(normalize-space(replace(., '\[\d*\]', '')), '&quot;', '')"/>
        <xsl:text>"</xsl:text>
      </xsl:if>
      <xsl:text>&#xa;</xsl:text>
    </xsl:if>
    <xsl:for-each select="@*">
      <xsl:if test="$showCollectionName">
        <xsl:value-of select="$collectionName"/>
        <xsl:value-of select="$delimiter"/>
      </xsl:if>
      <xsl:if test="$showFilename">
        <xsl:value-of select="$fileName"/>
        <xsl:value-of select="$delimiter"/>
      </xsl:if>
      <xsl:value-of select="normalize-space(replace(saxon:path(), '\[\d*\]', ''))"/>
      <xsl:if test="$showValues">
        <xsl:value-of select="$delimiter"/>
        <xsl:text>"</xsl:text>
        <!-- remove double quotes -->
        <xsl:value-of select="normalize-space(replace(., '&quot;',''))"/>
        <xsl:text>"</xsl:text>
      </xsl:if>
      <xsl:text>&#xa;</xsl:text>
    </xsl:for-each>
    <xsl:apply-templates select="*">
      <xsl:with-param name="collectionName" select="$collectionName"/>
      <xsl:with-param name="fileName" select="$fileName"/>
    </xsl:apply-templates>
  </xsl:template>
</xsl:stylesheet>
