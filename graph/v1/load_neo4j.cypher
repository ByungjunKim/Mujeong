// 『무정』 그래프 적재 (Neo4j 5 · AuraDB Free)
// BASE는 CSV가 있는 주소. 저장소의 graph/v1/ 을 그대로 읽는다(다른 판이면 v1을 바꾼다).
// 노드는 MERGE라 다시 넣어도 두 번 생기지 않는다. 관계는 CREATE이므로 다시 넣기 전에
//   MATCH (n) DETACH DELETE n;   으로 비운다.
:param BASE => 'https://raw.githubusercontent.com/ByungjunKim/Mujeong/main/graph/v1/';


CREATE CONSTRAINT person_id IF NOT EXISTS FOR (n:Person) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT place_id IF NOT EXISTS FOR (n:Place) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT org_id IF NOT EXISTS FOR (n:Org) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT object_id IF NOT EXISTS FOR (n:Object) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT chapter_id IF NOT EXISTS FOR (n:Chapter) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT paragraph_id IF NOT EXISTS FOR (n:Paragraph) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT utterance_id IF NOT EXISTS FOR (n:Utterance) REQUIRE n.id IS UNIQUE;

LOAD CSV WITH HEADERS FROM $BASE + 'nodes_Person.csv' AS row
MERGE (n:Person {id: row.id}) SET n.name = row.name, n.aliases = row.aliases, n.kind = row.kind, n.sex = row.sex, n.cert = row.cert;

LOAD CSV WITH HEADERS FROM $BASE + 'nodes_Place.csv' AS row
MERGE (n:Place {id: row.id}) SET n.name = row.name, n.aliases = row.aliases, n.kind = row.kind, n.sex = row.sex, n.cert = row.cert;

LOAD CSV WITH HEADERS FROM $BASE + 'nodes_Org.csv' AS row
MERGE (n:Org {id: row.id}) SET n.name = row.name, n.aliases = row.aliases, n.kind = row.kind, n.sex = row.sex, n.cert = row.cert;

LOAD CSV WITH HEADERS FROM $BASE + 'nodes_Object.csv' AS row
MERGE (n:Object {id: row.id}) SET n.name = row.name, n.aliases = row.aliases, n.kind = row.kind, n.sex = row.sex, n.cert = row.cert;

LOAD CSV WITH HEADERS FROM $BASE + 'nodes_Chapter.csv' AS row
MERGE (n:Chapter {id: row.id}) SET n.n = row.n, n.type = row.type, n.order = row.order, n.title = row.title, n.source = row.source, n.resp = row.resp;

LOAD CSV WITH HEADERS FROM $BASE + 'nodes_Paragraph.csv' AS row
MERGE (n:Paragraph {id: row.id}) SET n.chapter = row.chapter, n.seq = row.seq, n.order = row.order, n.text = row.text;

LOAD CSV WITH HEADERS FROM $BASE + 'nodes_Utterance.csv' AS row
MERGE (n:Utterance {id: row.id}) SET n.text = row.text, n.aloud = row.aloud, n.direct = row.direct, n.chapter = row.chapter, n.paragraph = row.paragraph, n.who = row.who;

LOAD CSV WITH HEADERS FROM $BASE + 'rels_IN_Paragraph_Chapter.csv' AS row
MATCH (s:Paragraph {id: row.start}), (e:Chapter {id: row.end})
CREATE (s)-[r:IN]->(e);

LOAD CSV WITH HEADERS FROM $BASE + 'rels_MENTIONED_IN_Place_Paragraph.csv' AS row
MATCH (s:Place {id: row.start}), (e:Paragraph {id: row.end})
CREATE (s)-[r:MENTIONED_IN]->(e) SET r.surface = row.surface, r.tag = row.tag;

LOAD CSV WITH HEADERS FROM $BASE + 'rels_MENTIONED_IN_Person_Paragraph.csv' AS row
MATCH (s:Person {id: row.start}), (e:Paragraph {id: row.end})
CREATE (s)-[r:MENTIONED_IN]->(e) SET r.surface = row.surface, r.tag = row.tag;

LOAD CSV WITH HEADERS FROM $BASE + 'rels_IN_Utterance_Paragraph.csv' AS row
MATCH (s:Utterance {id: row.start}), (e:Paragraph {id: row.end})
CREATE (s)-[r:IN]->(e);

LOAD CSV WITH HEADERS FROM $BASE + 'rels_THINKS_Person_Utterance.csv' AS row
MATCH (s:Person {id: row.start}), (e:Utterance {id: row.end})
CREATE (s)-[r:THINKS]->(e);

LOAD CSV WITH HEADERS FROM $BASE + 'rels_SAYS_Person_Utterance.csv' AS row
MATCH (s:Person {id: row.start}), (e:Utterance {id: row.end})
CREATE (s)-[r:SAYS]->(e);

LOAD CSV WITH HEADERS FROM $BASE + 'rels_MENTIONED_IN_Org_Paragraph.csv' AS row
MATCH (s:Org {id: row.start}), (e:Paragraph {id: row.end})
CREATE (s)-[r:MENTIONED_IN]->(e) SET r.surface = row.surface, r.tag = row.tag;

LOAD CSV WITH HEADERS FROM $BASE + 'rels_REFERS_TO_Utterance_Person.csv' AS row
MATCH (s:Utterance {id: row.start}), (e:Person {id: row.end})
CREATE (s)-[r:REFERS_TO]->(e) SET r.surface = row.surface;

LOAD CSV WITH HEADERS FROM $BASE + 'rels_SAYS_Org_Utterance.csv' AS row
MATCH (s:Org {id: row.start}), (e:Utterance {id: row.end})
CREATE (s)-[r:SAYS]->(e);

LOAD CSV WITH HEADERS FROM $BASE + 'rels_MENTIONED_IN_Object_Paragraph.csv' AS row
MATCH (s:Object {id: row.start}), (e:Paragraph {id: row.end})
CREATE (s)-[r:MENTIONED_IN]->(e) SET r.surface = row.surface, r.tag = row.tag;
