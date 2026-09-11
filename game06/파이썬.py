print("================================ 1 ================================")
def add(a,b):
    return a+b


result = add(3,5)
print(result)

print("================================ 2 ================================")


lst = ["사과","바나나", "체리"]

print(len(lst))


for i in lst:
    print(i)    

print("================================ 3 ================================")

#리스트에 값을 추가,삭제
lst.append("감체리")
print(lst)

lst.remove("바나나")
print(lst)

print("================================ 4 ================================")
#Tuple(튜플) : 리스트와 비슷하지만, 수정이 불가능하다.
tup = ("사과1","바나나2", "체리3")
print(len(tup))  
print(type(tup))  
for i in tup:
    print(i)    



print("================================ 5 ================================")
def times(a,b):
    return a*b, a+b

result = times(3,5)
print(result)   
print(type(result)) 
   

