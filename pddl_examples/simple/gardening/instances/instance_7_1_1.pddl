;; Enrico Scala (enricos83@gmail.com) and Miquel Ramirez (miquel.ramirez@gmail.com)
(define (problem instance_7_1_1)
  (:domain mt-plant-watering-constrained)
  (:objects
    agent1 - agent
	tap1 - tap
	plant1 - plant
  )

  (:init
    (= (max_int) 20)
	(= (maxx) 7)
	(= (minx) 1)
	(= (maxy) 7)
	(= (miny) 1)
	(= (carrying) 0)
	(= (total_poured) 0)
	(= (total_loaded) 0)
	(= (poured plant1) 0)
	(= (x agent1) 1)
	(= (y agent1) 5)
	(= (x plant1) 2)
	(= (y plant1) 2)
	(= (x tap1) 2)
	(= (y tap1) 2)
  )

  (:goal (and 
    (= (poured plant1) 1)
	(= (total_poured) (poured plant1) )
  ))

  
  

  
)